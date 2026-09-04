import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "monitor_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgrespassword")

def obtener_conexion():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

def guardar_producto_y_precio(datos_producto: dict, url: str) -> bool:
    if not datos_producto:
        return False

    conexion = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        # 1. Insertar o recuperar el producto en monitored_products
        query_producto = """
            INSERT INTO monitored_products (name, target_url, category)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
            RETURNING id;
        """
        cursor.execute(query_producto, (datos_producto["titulo"], url, "Libros"))
        resultado = cursor.fetchone()

        if resultado:
            product_id = resultado[0]
        else:
            cursor.execute("SELECT id FROM monitored_products WHERE target_url = %s;", (url,))
            product_id = cursor.fetchone()[0]

        # 2. Consultar el último precio registrado en price_logs para detectar variaciones
        query_ultimo_precio = """
            SELECT price FROM price_logs 
            WHERE product_id = %s 
            ORDER BY scraped_at DESC 
            LIMIT 1;
        """
        cursor.execute(query_ultimo_precio, (product_id,))
        ultimo_registro = cursor.fetchone()

        precio_nuevo = datos_producto["precio"]

        if ultimo_registro:
            precio_anterior = float(ultimo_registro[0])
            
            # Si el precio cambió, generamos una alerta
            if precio_anterior != precio_nuevo:
                diferencia = precio_nuevo - precio_anterior
                porcentaje_cambio = (diferencia / precio_anterior) * 100

                query_alerta = """
                    INSERT INTO price_alerts (product_id, previous_price, new_price, percentage_change)
                    VALUES (%s, %s, %s, %s);
                """
                cursor.execute(query_alerta, (product_id, precio_anterior, precio_nuevo, porcentaje_cambio))
                print(f"[ALERTA] ¡Cambio de precio detectado! Anterior: {precio_anterior} -> Nuevo: {precio_nuevo} ({porcentaje_cambio:+.2f}%)")
            else:
                print(f"[INFO] El precio se mantiene sin cambios: {precio_nuevo}")

        # 3. Insertar el nuevo precio en price_logs
        query_log = """
            INSERT INTO price_logs (product_id, price, currency, is_available)
            VALUES (%s, %s, %s, %s);
        """
        cursor.execute(query_log, (
            product_id,
            precio_nuevo,
            datos_producto["moneda"],
            datos_producto["disponible"]
        ))

        conexion.commit()
        print(f"[EXITO] Registro actualizado en BD (ID Producto: {product_id})")
        
        cursor.close()
        return True

    except Exception as error:
        if conexion:
            conexion.rollback()
        print(f"[ERROR BD] No se pudo procesar la transacción: {error}")
        return False

    finally:
        if conexion:
            conexion.close()
def obtener_productos_activos() -> list:
    """
    Retorna una lista de tuplas (id, target_url, name) con todos los productos activos a monitorear.
    """
    conexion = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        query = "SELECT id, target_url, name FROM monitored_products WHERE is_active = TRUE;"
        cursor.execute(query)
        productos = cursor.fetchall()
        
        cursor.close()
        return productos
    except Exception as error:
        print(f"[ERROR BD] No se pudieron obtener los productos activos: {error}")
        return []
    finally:
        if conexion:
            conexion.close()