from flask import Flask, jsonify
import sqlite3

app = Flask(__name__)
DB_PATH = "db/base_plantas_agroecologia.sqlite"

@app.route("/")
def home():
    return jsonify({"message": "API de Agroecología funcionando"})

@app.route("/plantas")
def get_plantas():
    conn = sqlite3.connect(DB_PATH)
    df = conn.execute("SELECT * FROM plantas_base").fetchall()
    cols = [col[0] for col in conn.execute("PRAGMA table_info(plantas_base)")]
    conn.close()
    plantas = [dict(zip(cols, row)) for row in df]
    return jsonify(plantas)

@app.route("/plantas/<id_planta>")
def get_planta(id_planta):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("SELECT * FROM plantas_base WHERE id_planta = ?", (id_planta,))
    row = cursor.fetchone()
    cols = [col[0] for col in conn.execute("PRAGMA table_info(plantas_base)")]
    conn.close()
    if row:
        return jsonify(dict(zip(cols, row)))
    else:
        return jsonify({"error": "Planta no encontrada"}), 404

@app.route("/resolver_nombre_comun/<nombre>")
def resolver_nombre_comun(nombre):
    conn = sqlite3.connect(DB_PATH)
    nombre = nombre.lower()
    param = f"%{nombre}%"

    # Buscar tablas con columna 'nombre_comun'
    query_tablas = """
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
    """
    tablas = conn.execute(query_tablas).fetchall()
    tablas = [t[0] for t in tablas]

    coincidencias = []
    for tabla in tablas:
        try:
            # Verifica si la tabla contiene las columnas necesarias
            columnas = [col[1] for col in conn.execute(f"PRAGMA table_info({tabla})")]
            if "nombre_comun" in columnas and "id_planta" in columnas:
                query = f"""
                    SELECT DISTINCT nombre_comun, nombre_cientifico, id_planta
                    FROM {tabla}
                    WHERE LOWER(nombre_comun) LIKE ?
                """
                filas = conn.execute(query, (param,)).fetchall()
                for fila in filas:
                    coincidencias.append({
                        "nombre_comun": fila[0],
                        "nombre_cientifico": fila[1],
                        "id_planta": fila[2],
                        "fuente": tabla
                    })
        except Exception as e:
            continue

    conn.close()

    if coincidencias:
        return jsonify(coincidencias)
    else:
        return jsonify({"message": "No se encontró ninguna coincidencia"}), 404


@app.route("/ficha_completa/<id_planta>")
def ficha_completa(id_planta):
    conn = sqlite3.connect(DB_PATH)
    id_planta = id_planta.strip()

    resultado = {
        "id_planta": id_planta,
        "datos": {}
    }

    # Primero: info principal desde plantas_base
    try:
        cursor = conn.execute("SELECT * FROM plantas_base WHERE id_planta = ?", (id_planta,))
        row = cursor.fetchone()
        if row:
            cols = [col[0] for col in conn.execute("PRAGMA table_info(plantas_base)")]
            resultado["datos"]["plantas_base"] = dict(zip(cols, row))
        else:
            resultado["datos"]["plantas_base"] = {"mensaje": "Planta no encontrada en plantas_base"}
    except Exception as e:
        resultado["datos"]["plantas_base"] = {"error": str(e)}

    # Luego: buscar en todas las demás tablas
    tablas = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
    tablas = [t[0] for t in tablas if t != "plantas_base"]

    for tabla in tablas:
        try:
            columnas = [col[1] for col in conn.execute(f"PRAGMA table_info({tabla})")]
            if "id_planta" in columnas:
                query = f"SELECT * FROM {tabla} WHERE id_planta = ?"
                rows = conn.execute(query, (id_planta,)).fetchall()
                if rows:
                    resultado["datos"][tabla] = []
                    for row in rows:
                        resultado["datos"][tabla].append(dict(zip(columnas, row)))
        except Exception as e:
            resultado["datos"][tabla] = {"error": str(e)}

    conn.close()
    return jsonify(resultado)


if __name__ == "__main__":
    app.run(debug=True)