import os
import io
import csv
import json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, Response
from pydantic import BaseModel
from typing import Optional
from database import obtener_conexion
from scraper import extraer_precio_producto

app = FastAPI(
    title="Tarify API",
    description="Endpoints para consultar productos monitoreados, lecturas históricas, alertas y exportaciones.",
    version="1.3.0"
)

class NuevoProductoRequest(BaseModel):
    name: str
    target_url: str
    category: str = "General"
    target_price: Optional[float] = None

app.mount("/static", StaticFiles(directory="src/static"), name="static")

@app.get("/")
def read_root():
    return FileResponse(
        "src/static/index.html",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )

@app.post("/api/v1/products")
def agregar_producto(producto: NuevoProductoRequest):
    conexion = None
    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            query_prod = """
                INSERT INTO monitored_products (name, target_url, category, target_price, is_active)
                VALUES (%s, %s, %s, %s, TRUE)
                RETURNING id;
            """
            cursor.execute(query_prod, (producto.name, producto.target_url, producto.category, producto.target_price))
            nuevo_id = cursor.fetchone()[0]
            
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
                    p.target_price,
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
                WHERE p.is_active = TRUE
                ORDER BY p.id DESC;
            """
            cursor.execute(query)
            filas = cursor.fetchall()
        
        productos = []
        for id_prod, nombre, url, cat, t_price, activo, fecha, precio in filas:
            with conexion.cursor() as cur_hist:
                cur_hist.execute("""
                    SELECT price FROM price_logs 
                    WHERE product_id = %s 
                    ORDER BY scraped_at ASC LIMIT 10;
                """, (id_prod,))
                historial = [float(h[0]) for h in cur_hist.fetchall()]

            productos.append({
                "id": id_prod,
                "name": nombre,
                "target_url": url,
                "category": cat,
                "target_price": float(t_price) if t_price is not None else None,
                "is_active": activo,
                "created_at": fecha.isoformat(),
                "last_price": float(precio) if precio is not None else None,
                "price_history": historial
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
                WHERE p.is_active = TRUE
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
            # Eliminar registros relacionados primero para evitar huérfanos
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

# ---------------------------------------------------------
# EXPORTACIONES FILTRADAS: SOLO PRODUCTOS ACTIVOS Y SU ÚLTIMO REGISTRO
# ---------------------------------------------------------

@app.get("/api/v1/export/csv")
def exportar_csv():
    conexion = None
    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            # Trae ÚNICAMENTE el último precio registrado de cada producto ACTIVO
            query = """
                SELECT DISTINCT ON (p.id)
                    p.name AS producto,
                    p.category AS categoria,
                    pl.price AS precio_usd,
                    pl.scraped_at AS fecha_registro
                FROM monitored_products p
                JOIN price_logs pl ON pl.product_id = p.id
                WHERE p.is_active = TRUE
                ORDER BY p.id, pl.scraped_at DESC;
            """
            cursor.execute(query)
            filas = cursor.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Producto", "Categoria", "Precio_USD", "Fecha_Registro"])

        for prod, cat, precio, fecha in filas:
            writer.writerow([prod, cat, float(precio), fecha.isoformat()])

        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=tarify_catalogo_activo.csv"}
        )
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Error al exportar CSV: {error}")
    finally:
        if conexion:
            conexion.close()

@app.get("/api/v1/export/json")
def exportar_json():
    conexion = None
    try:
        conexion = obtener_conexion()
        with conexion.cursor() as cursor:
            # Trae ÚNICAMENTE el último precio registrado de cada producto ACTIVO
            query = """
                SELECT DISTINCT ON (p.id)
                    p.name AS producto,
                    p.category AS categoria,
                    pl.price AS precio_usd,
                    pl.scraped_at AS fecha_registro
                FROM monitored_products p
                JOIN price_logs pl ON pl.product_id = p.id
                WHERE p.is_active = TRUE
                ORDER BY p.id, pl.scraped_at DESC;
            """
            cursor.execute(query)
            filas = cursor.fetchall()

        datos = []
        for prod, cat, precio, fecha in filas:
            datos.append({
                "producto": prod,
                "categoria": cat,
                "precio_usd": float(precio),
                "fecha_registro": fecha.isoformat()
            })

        contenido_json = json.dumps(datos, indent=4, ensure_ascii=False)
        return Response(
            content=contenido_json,
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=tarify_catalogo_activo.json"}
        )
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Error al exportar JSON: {error}")
    finally:
        if conexion:
            conexion.close()