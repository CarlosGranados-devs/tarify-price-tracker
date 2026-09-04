import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from database import obtener_conexion
from scraper import extraer_precio_producto

app = FastAPI(
    title="Tarify API",
    description="Endpoints para consultar productos monitoreados, lecturas históricas y alertas.",
    version="1.0.0"
)

class NuevoProductoRequest(BaseModel):
    name: str
    target_url: str
    category: str = "General"

app.mount("/static", StaticFiles(directory="src/static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("src/static/index.html")

@app.post("/api/v1/products")
def agregar_producto(producto: NuevoProductoRequest):
    conexion = None
    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            # 1. Registrar producto
            query_prod = """
                INSERT INTO monitored_products (name, target_url, category, is_active)
                VALUES (%s, %s, %s, TRUE)
                RETURNING id;
            """
            cursor.execute(query_prod, (producto.name, producto.target_url, producto.category))
            nuevo_id = cursor.fetchone()[0]
            
            # 2. Raspado inmediato extrayendo el precio real del diccionario
            resultado = extraer_precio_producto(producto.target_url)
            
            precio_flotante = None
            if isinstance(resultado, dict):
                precio_flotante = resultado.get('precio')
            elif isinstance(resultado, (int, float)):
                precio_flotante = resultado

            if precio_flotante is not None:
                query_price = """
                    INSERT INTO price_logs (product_id, price)
                    VALUES (%s, %s);
                """
                cursor.execute(query_price, (nuevo_id, precio_flotante))
                
            conexion.commit()
            
        return {"status": "exito", "message": "Producto registrado y procesado", "id": nuevo_id}
    except Exception as error:
        if conexion:
            conexion.rollback()
        raise HTTPException(status_code=500, detail=f"Error al registrar producto: {error}")
    finally:
        if conexion:
            conexion.close()

@app.get("/api/v1/products")
def listar_productos():
    conexion = None
    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            query = """
                SELECT 
                    p.id,
                    p.name,
                    p.target_url,
                    p.category,
                    p.is_active,
                    p.created_at,
                    (
                        SELECT r.price 
                        FROM price_logs r 
                        WHERE r.product_id = p.id 
                        ORDER BY r.scraped_at DESC 
                        LIMIT 1
                    ) AS last_price
                FROM monitored_products p
                ORDER BY p.id DESC;
            """
            cursor.execute(query)
            filas = cursor.fetchall()
        
        productos = []
        for id_prod, nombre, url, cat, activo, fecha, precio in filas:
            productos.append({
                "id": id_prod,
                "name": nombre,
                "target_url": url,
                "category": cat,
                "is_active": activo,
                "created_at": fecha.isoformat(),
                "last_price": float(precio) if precio is not None else None
            })
            
        return {"count": len(productos), "data": productos}
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Error en base de datos: {error}")
    finally:
        if conexion:
            conexion.close()

@app.get("/api/v1/alerts")
def listar_alertas():
    conexion = None
    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            query = """
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
            cursor.execute(query)
            filas = cursor.fetchall()
        
        alertas = []
        for alt_id, nombre, ant, nuevo, pct, fecha in filas:
            alertas.append({
                "id": alt_id,
                "product_name": nombre,
                "previous_price": float(ant),
                "new_price": float(nuevo),
                "percentage_change": float(pct),
                "triggered_at": fecha.isoformat()
            })
            
        return {"count": len(alertas), "data": alertas}
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Error en base de datos: {error}")
    finally:
        if conexion:
            conexion.close()

@app.delete("/api/v1/products/{product_id}")
def eliminar_producto(product_id: int):
    conexion = None
    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            cursor.execute("DELETE FROM price_logs WHERE product_id = %s;", (product_id,))
            cursor.execute("DELETE FROM price_alerts WHERE product_id = %s;", (product_id,))
            cursor.execute("DELETE FROM monitored_products WHERE id = %s;", (product_id,))
            conexion.commit()
        return {"status": "exito", "message": f"Producto {product_id} eliminado"}
    except Exception as error:
        if conexion:
            conexion.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar: {error}")
    finally:
        if conexion:
            conexion.close()