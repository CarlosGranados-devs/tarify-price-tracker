import time
from database import obtener_conexion
from scraper import extraer_precio_producto
from notifications import enviar_alerta_telegram, enviar_alerta_email

def procesar_monitoreo():
    conexion = None
    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            # Obtener todos los productos activos con su target_price
            cursor.execute("SELECT id, name, target_url, target_price FROM monitored_products WHERE is_active = TRUE;")
            productos = cursor.fetchall()

            print(f"\n--- [Scheduler] Iniciando ronda de raspado ({len(productos)} productos) ---")

            for prod_id, nombre, url, target_price in productos:
                resultado = extraer_precio_producto(url)
                
                precio_actual = None
                if isinstance(resultado, dict):
                    precio_actual = resultado.get('precio')
                elif isinstance(resultado, (int, float)):
                    precio_actual = resultado

                if precio_actual is None:
                    print(f"  ❌ No se pudo extraer precio de '{nombre}'")
                    continue

                # Obtener el último precio registrado
                cursor.execute("""
                    SELECT price FROM price_logs 
                    WHERE product_id = %s 
                    ORDER BY scraped_at DESC LIMIT 1;
                """, (prod_id,))
                ultimo_registro = cursor.fetchone()

                # Insertar la nueva lectura
                cursor.execute("""
                    INSERT INTO price_logs (product_id, price) 
                    VALUES (%s, %s);
                """, (prod_id, precio_actual))

                # Evaluar variación
                if ultimo_registro is not None:
                    precio_anterior = float(ultimo_registro[0])
                    t_price_float = float(target_price) if target_price is not None else None

                    # Criterio: bajó de precio Y (no hay target OR el precio actual es <= target)
                    cumple_target = (t_price_float is None) or (precio_actual <= t_price_float)

                    if precio_actual < precio_anterior and cumple_target:
                        variacion_pct = ((precio_anterior - precio_actual) / precio_anterior) * 100
                        print(f"  🔥 ¡ALERTA DISPARADA! '{nombre}': ${precio_anterior:.2f} -> ${precio_actual:.2f} (-{variacion_pct:.1f}%)")

                        # Registrar en la tabla price_alerts
                        cursor.execute("""
                            INSERT INTO price_alerts (product_id, previous_price, new_price, percentage_change)
                            VALUES (%s, %s, %s, %s);
                        """, (prod_id, precio_anterior, precio_actual, variacion_pct))

                        # Disparar alertas
                        enviar_alerta_telegram(nombre, precio_anterior, precio_actual, url)
                        enviar_alerta_email(nombre, precio_anterior, precio_actual, url)

                    elif precio_actual < precio_anterior:
                        print(f"  📉 Bajó a ${precio_actual:.2f} pero aún no alcanza el Target (${t_price_float:.2f})")
                    elif precio_actual > precio_anterior:
                        print(f"  📈 Subida de precio en '{nombre}': ${precio_anterior:.2f} -> ${precio_actual:.2f}")
                    else:
                        print(f"  ➖ Sin cambios en '{nombre}': ${precio_actual:.2f}")
                else:
                    print(f"  ✅ Primer precio registrado para '{nombre}': ${precio_actual:.2f}")

            conexion.commit()
            print("--- [Scheduler] Ronda completada exitosamente ---\n")

    except Exception as error:
        if conexion:
            conexion.rollback()
        print(f"[Scheduler Error] Ocurrió un fallo durante el proceso: {error}")
    finally:
        if conexion:
            conexion.close()

if __name__ == "__main__":
    while True:
        procesar_monitoreo()
        time.sleep(60)