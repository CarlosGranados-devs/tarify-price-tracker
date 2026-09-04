import os
import psycopg2
from dotenv import load_dotenv

# Cargamos las variables del archivo .env si existe
load_dotenv()

# Configuración de conexión (usamos valores por defecto si no existen en .env)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "monitor_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgrespassword")

def obtener_conexion():
    """
    Establece y retorna una conexión con la base de datos PostgreSQL.
    """
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

def guardar_producto_y_precio(datos_producto: dict, url: str) -> bool:
    """
    Inserta o recupera un producto en 'monitored_products' y guarda su lectura actual en 'price_logs'.
    """
    if not datos_producto:
        return False

    conexion = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        # 1. Verificar si el producto ya existe o insertarlo
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
            # Si ya existía, consultamos su ID
            cursor.execute("SELECT id FROM monitored_products WHERE target_url = %s;", (url,))
            product_id = cursor.fetchone()[0]

        # 2. Insertar la lectura actual de precio en price_logs
        query_log = """
            INSERT INTO price_logs (product_id, price, currency, is_available)
            VALUES (%s, %s, %s, %s);
        """
        cursor.execute(query_log, (
            product_id,
            datos_producto["precio"],
            datos_producto["moneda"],
            datos_producto["disponible"]
        ))

        # Guardar los cambios permanentemente en la BD
        conexion.commit()
        print(f"[EXITO] Guardado en BD: '{datos_producto['titulo']}' - {datos_producto['moneda']} {datos_producto['precio']} (ID Producto: {product_id})")
        
        cursor.close()
        return True

    except Exception as error:
        if conexion:
            conexion.rollback()  # Deshace cambios si ocurre un error
        print(f"[ERROR BD] No se pudo guardar el registro: {error}")
        return False

    finally:
        if conexion:
            conexion.close()