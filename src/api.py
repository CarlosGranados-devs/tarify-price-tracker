import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from database import obtener_conexion

app = FastAPI(
    title="Tarify API",
    description="Endpoints para consultar productos monitoreados, lecturas históricas y alertas.",
    version="1.0.0"
)

# Esquema de validación para nuevos productos
class NuevoProductoRequest(BaseModel):
    name: str
    target_url: str
    category: str = "General"

# Montar carpeta de archivos estáticos
app.mount("/static", StaticFiles(directory="src/static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("src/static/index.html")

@app.post("/api/v1/products")
def agregar_producto(producto: NuevoProductoRequest):
    conexion = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        query = """
            INSERT INTO monitored_products (name, target_url, category, is_active)
            VALUES (%s, %s, %s, TRUE)
            RETURNING id;
        """
        cursor.execute(query, (producto.name, producto.target_url, producto.category))
        nuevo_id = cursor.fetchone()[0]
        conexion.commit()
        cursor.close()
        
        return {"status": "exito", "message": "Producto registrado correctamente", "id": nuevo_id}
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
        cursor = conexion.cursor()
        
        query = "SELECT id, name, target_url, category, is_active, created_at FROM monitored_products;"
        cursor.execute(query)
        filas = cursor.fetchall()
        cursor.close()
        
        productos = []
        for id_prod, nombre, url, cat, activo, fecha in filas:
            productos.append({
                "id": id_prod,
                "name": nombre,
                "target_url": url,
                "category": cat,
                "is_active": activo,
                "created_at": fecha.isoformat()
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
        cursor = conexion.cursor()
        
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
        cursor.close()
        
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