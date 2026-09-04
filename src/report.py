import psycopg2
from database import obtener_conexion

def generar_reporte_resumen():
    """
    Consulta y muestra en consola un resumen de los productos monitoreados,
    sus ultimos precios y las alertas generadas.
    """
    conexion = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        print("\n" + "=" * 70)
        print("[REPORTE] HISTORICO DE PRODUCTOS Y ULTIMOS PRECIOS")
        print("=" * 70)

        query_precios = """
            SELECT 
                p.id,
                p.name,
                l.price,
                l.currency,
                l.scraped_at
            FROM monitored_products p
            JOIN price_logs l ON p.id = l.product_id
            WHERE l.scraped_at = (
                SELECT MAX(scraped_at) 
                FROM price_logs 
                WHERE product_id = p.id
            )
            ORDER BY p.id ASC;
        """
        cursor.execute(query_precios)
        filas = cursor.fetchall()

        print(f"{'ID':<5} | {'PRODUCTO':<30} | {'PRECIO':<12} | {'ULTIMA LECTURA'}")
        print("-" * 70)
        for prod_id, nombre, precio, moneda, fecha in filas:
            print(f"{prod_id:<5} | {nombre[:28]:<30} | {moneda} {precio:<7.2f} | {fecha.strftime('%Y-%m-%d %H:%M:%S')}")

        print("\n" + "=" * 70)
        print("[REPORTE] HISTORICO DE ALERTAS DE VARIACION")
        print("=" * 70)

        query_alertas = """
            SELECT 
                a.id,
                p.name,
                a.previous_price,
                a.new_price,
                a.percentage_change,
                a.triggered_at
            FROM price_alerts a
            JOIN monitored_products p ON a.product_id = p.id
            ORDER BY a.triggered_at DESC;
        """
        cursor.execute(query_alertas)
        alertas = cursor.fetchall()

        if not alertas:
            print("[INFO] No se han registrado alertas de cambio de precio aun.")
        else:
            print(f"{'ID':<5} | {'PRODUCTO':<25} | {'ANTERIOR':<10} | {'NUEVO':<10} | {'CAMBIO (%)':<10} | {'FECHA'}")
            print("-" * 75)
            for alt_id, nombre, ant, nuevo, pct, fecha in alertas:
                signo = "+" if pct > 0 else ""
                print(f"{alt_id:<5} | {nombre[:23]:<25} | {ant:<10.2f} | {nuevo:<10.2f} | {signo}{pct:<9.2f}% | {fecha.strftime('%Y-%m-%d %H:%M:%S')}")

        print("=" * 75 + "\n")

        cursor.close()
    except Exception as error:
        print(f"[ERROR] No se pudo generar el reporte: {error}")
    finally:
        if conexion:
            conexion.close()

if __name__ == "__main__":
    generar_reporte_resumen()