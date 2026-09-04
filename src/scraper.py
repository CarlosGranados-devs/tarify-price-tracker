import re
import requests
from bs4 import BeautifulSoup

# Cabeceras completas para simular una navegación real
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
}

def extraer_precio_producto(url: str):
    """
    Extrae el precio y título de cualquier producto o e-commerce general.
    Utiliza metadatos estándar (OpenGraph / JSON-LD / Schema.org) y selectores CSS dinámicos.
    """
    try:
        session = requests.Session()
        respuesta = session.get(url, headers=HEADERS, timeout=12)
        
        if respuesta.status_code != 200:
            print(f"[Scraper Warning] Status code {respuesta.status_code} para {url}")
            return None

        soup = BeautifulSoup(respuesta.content, 'html.parser')

        # ---------------------------------------------------------
        # 1. EXTRACCIÓN DE TÍTULO AGNÓSTICO
        # ---------------------------------------------------------
        titulo = None
        
        # Meta etiquetas universales OpenGraph / Twitter Cards
        og_title = soup.find('meta', property='og:title') or soup.find('meta', name='twitter:title')
        if og_title and og_title.get('content'):
            titulo = og_title['content'].strip()
            
        if not titulo:
            h1 = soup.find('h1')
            if h1:
                titulo = h1.text.strip()
                
        if not titulo and soup.title:
            titulo = soup.title.text.strip()

        if not titulo:
            titulo = "Producto Monitoreado"

        # ---------------------------------------------------------
        # 2. EXTRACCIÓN DE PRECIO AGNÓSTICO
        # ---------------------------------------------------------
        precio = None

        # Estrategia A: Meta etiquetas OpenGraph / Schema.org (Standard E-commerce)
        meta_price = (
            soup.find('meta', property='product:price:amount') or
            soup.find('meta', property='og:price:amount') or
            soup.find('meta', itemprop='price')
        )
        if meta_price and meta_price.get('content'):
            try:
                precio = float(meta_price['content'].replace(',', ''))
            except ValueError:
                pass

        # Estrategia B: Amazon / Retailers Complejos
        if precio is None and "amazon" in url.lower():
            # Intentar capturar precio flotante de Amazon
            price_offscreen = soup.find('span', class_='a-offscreen')
            if price_offscreen:
                match = re.search(r'[\d\.\,]+', price_offscreen.text)
                if match:
                    try:
                        precio = float(match.group().replace(',', ''))
                    except ValueError:
                        pass
            
            if precio is None:
                price_whole = soup.find('span', class_='a-price-whole')
                price_fraction = soup.find('span', class_='a-price-fraction')
                if price_whole:
                    whole = price_whole.text.replace('.', '').replace(',', '').strip()
                    frac = price_fraction.text.strip() if price_fraction else "00"
                    try:
                        precio = float(f"{whole}.{frac}")
                    except ValueError:
                        pass

        # Estrategia C: Selectores Genéricos de E-Commerce (Clases / IDs con "price")
        if precio is None:
            # Buscar elementos que tengan clases o ids como 'price', 'precio', 'amount'
            elementos_precio = soup.find_all(['span', 'div', 'p', 'b'], class_=re.compile(r'price|precio|amount|val', re.I))
            for elem in elementos_precio:
                # Extraer números que coincidan con formato monetario
                match = re.search(r'\$\s*([\d\.\,]+)', elem.text)
                if match:
                    try:
                        cand_price = float(match.group(1).replace(',', ''))
                        if cand_price > 0:
                            precio = cand_price
                            break
                    except ValueError:
                        continue

        # Estrategia D: Expresión regular sobre todo el texto para capturar patrones de precio ($XX.XX)
        if precio is None:
            matches = re.findall(r'\$\s*(\d+\.\d{2})', respuesta.text)
            if matches:
                try:
                    precio = float(matches[0])
                except ValueError:
                    pass

        if precio is None:
            return None

        return {
            "titulo": titulo,
            "precio": precio,
            "moneda": "USD",
            "disponible": True
        }

    except Exception as e:
        print(f"[Scraper Error] Error extrayendo precio de {url}: {e}")
        return None