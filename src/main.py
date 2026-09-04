import time
import random
from scraper import extraer_precio_producto
from database import obtener_productos_activos, guardar_producto_y_precio

def ejecutar_pipeline_monitoreo():
    """
    Funcion principal que consulta los productos registrados y ejecuta la extraccion
    y actualizacion de precios para cada uno.
    """
    print("=" * 60)
    print("[INICIO] CICLO DE MONITOREO DE PRECIOS")
    print("=" * 60)

    productos = obtener_productos_activos()

    if not productos:
        print("[INFO] No hay productos activos registrados para monitorear en la BD.")
        print("[INFO] Sugerencia: Inserta URLs en la tabla 'monitored_products'.")
        return

    print(f"[INFO] Se encontraron {len(productos)} productos activos para procesar.\n")

    exitosos = 0
    fallidos = 0

    for idx, (prod_id, url, nombre) in enumerate(productos, start=1):
        print(f"[{idx}/{len(productos)}] Procesando: '{nombre}'")
        print(f"URL: {url}")

        datos = extraer_precio_producto(url)

        if datos:
            guardado = guardar_producto_y_precio(datos, url)
            if guardado:
                exitosos += 1
            else:
                fallidos += 1
        else:
            fallidos += 1

        print("-" * 50)

        # Retardo etico aleatorio entre 2 y 4 segundos para evitar rate-limiting / bloqueos IP
        if idx < len(productos):
            espera = random.uniform(2.0, 4.0)
            time.sleep(espera)

    print("\n" + "=" * 60)
    print(f"[RESUMEN] EJECUCION COMPLETADA: {exitosos} Exitosos | {fallidos} Fallidos")
    print("=" * 60)

if __name__ == "__main__":
    ejecutar_pipeline_monitoreo()