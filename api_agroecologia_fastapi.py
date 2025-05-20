from fastapi import FastAPI
from fastapi.responses import JSONResponse
import sqlite3

app = FastAPI(title="API Agroecológica", version="1.0")
DB_PATH = "db/base_plantas_agroecologia.sqlite"

@app.get("/")
def home():
    return {"message": "API de Agroecología funcionando"}

@app.get("/plantas")
def get_plantas():
    conn = sqlite3.connect(DB_PATH)
    df = conn.execute("SELECT * FROM plantas_base").fetchall()
    cols = [col[0] for col in conn.execute("PRAGMA table_info(plantas_base)")]
    conn.close()
    plantas = [dict(zip(cols, row)) for row in df]
    return plantas

@app.get("/plantas/{id_planta}")
def get_planta(id_planta: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("SELECT * FROM plantas_base WHERE id_planta = ?", (id_planta,))
    row = cursor.fetchone()
    cols = [col[0] for col in conn.execute("PRAGMA table_info(plantas_base)")]
    conn.close()
    if row:
        return dict(zip(cols, row))
    return JSONResponse(status_code=404, content={"error": "Planta no encontrada"})

@app.get("/resolver_nombre_comun/{nombre}")
def resolver_nombre_comun(nombre: str):
    conn = sqlite3.connect(DB_PATH)
    nombre = nombre.lower()
    param = f"%{nombre}%"
    tablas = conn.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
    """).fetchall()
    tablas = [t[0] for t in tablas]

    coincidencias = []
    for tabla in tablas:
        try:
            columnas = [col[1] for col in conn.execute(f"PRAGMA table_info({tabla})")]
            if "nombre_comun" in columnas and "id_planta" in columnas:
                query = f"""
                    SELECT DISTINCT nombre_comun, nombre_cientifico, id_planta, fuente
                    FROM {tabla}
                    WHERE LOWER(nombre_comun) LIKE ?
                """
                filas = conn.execute(query, (param,)).fetchall()
                for fila in filas:
                    coincidencias.append({
                        "nombre_comun": fila[0],
                        "nombre_cientifico": fila[1],
                        "id_planta": fila[2],
                        "fuente": fila[3] if len(fila) > 3 else tabla
                    })
        except:
            continue

    conn.close()
    if coincidencias:
        return coincidencias
    return JSONResponse(status_code=404, content={"message": "No se encontró ninguna coincidencia"})

@app.get("/ficha_completa/{id_planta}")
def ficha_completa(id_planta: str):
    conn = sqlite3.connect(DB_PATH)
    id_planta = id_planta.strip()
    resultado = {"id_planta": id_planta, "datos": {}}

    try:
        cursor = conn.execute("SELECT * FROM plantas_base WHERE id_planta = ?", (id_planta,))
        row = cursor.fetchone()
        if row:
            cols = [col[0] for col in conn.execute("PRAGMA table_info(plantas_base)")]
            resultado["datos"]["plantas_base"] = dict(zip(cols, row))
        else:
            resultado["datos"]["plantas_base"] = {"mensaje": "No encontrada en plantas_base"}
    except Exception as e:
        resultado["datos"]["plantas_base"] = {"error": str(e)}

    tablas = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
    tablas = [t[0] for t in tablas if t[0] != "plantas_base"]

    for tabla in tablas:
        try:
            columnas = [col[1] for col in conn.execute(f"PRAGMA table_info({tabla})")]
            if "id_planta" in columnas:
                query = f"SELECT * FROM {tabla} WHERE id_planta = ?"
                rows = conn.execute(query, (id_planta,)).fetchall()
                if rows:
                    resultado["datos"][tabla] = [dict(zip(columnas, row)) for row in rows]
        except Exception as e:
            resultado["datos"][tabla] = {"error": str(e)}

    conn.close()
    return resultado


