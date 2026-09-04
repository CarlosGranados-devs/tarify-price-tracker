import requests
from bs4 import BeautifulSoup
import re

def extraer_precio_producto(url: str) -> dict:
    """
    Realiza una petición HTTP a una URL dada y extrae el título y el precio del producto.
    """
    # 1. Definimos un User-Agent para identificarnos como un navegador estándar
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        # 2. Enviamos la petición GET a la web
        respuesta = requests.get(url, headers=headers, timeout=10)
        
        # Lanza una excepción si la respuesta no es 200 OK
        respuesta.raise_for_status()

        # 3. Parseamos el contenido HTML recibido con BeautifulSoup
        soup = BeautifulSoup(respuesta.text, "html.parser")

        # 4. Extraemos el título del producto (ubicado en la etiqueta <h1>)
        titulo_element = soup.find("h1")
        titulo = titulo_element.text.strip() if titulo_element else "Desconocido"

        # 5. Extraemos el precio (ubicado en una clase CSS '.price_color')
        precio_element = soup.find("p", class_="price_color")
        
        if not precio_element:
            raise ValueError("No se pudo encontrar el elemento del precio en la página.")

        precio_texto = precio_element.text.strip()

        # 6. Limpieza de datos: Convertimos "£51.77" o "$1,250.00" a un float limpio (51.77)
        precio_limpio = re.sub(r"[^\d.]", "", precio_texto)
        precio_numeric = float(precio_limpio)

        return {
            "titulo": titulo,
            "precio": precio_numeric,
            "moneda": "GBP" if "£" in precio_texto else "USD",
            "disponible": True
        }

    except Exception as error:
        print(f"[ERROR] Falló la extracción en {url}: {error}")
        return None


# --- Bloque de ejecución ---
if __name__ == "__main__":
    from database import guardar_producto_y_precio

    url_prueba = "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
    
    print(f"Extrayendo información de: {url_prueba} ...")
    datos = extraer_precio_producto(url_prueba)
    
    if datos:
        print("\n--- Guardando en Base de Datos ---")
        guardar_producto_y_precio(datos, url_prueba)