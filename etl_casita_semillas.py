
# --- Código optimizado para Explorador Agroecológico ---
import streamlit as st
import pandas as pd
import re
import sqlite3
from rapidfuzz import fuzz

st.set_page_config(page_title="🔍 Explorador Limpio de Tablas Agroecológicas", layout="wide")
st.title("🌱 Explorador Limpio de Tablas Agroecológicas")


def limpiar_dataframe(df):
    columnas_con_separadores = [
        "nombre_comun", "efectos", "parte_utilizada", "aporte nutricional",
    ]
    
    columnas_excluir_capitalizar = ["nombre_cientifico"]

    def limpiar_celda(x):
        if not isinstance(x, str):
            return x

        # 1. Normaliza saltos de línea, tabs y espacios múltiples
        x = re.sub(r"[\n\r\t]+", " ", x)
        x = re.sub(r"\s+", " ", x).strip()

        # 2. Reconstruye palabras artificialmente separadas
        palabras_limpias = []
        for palabra in x.split():
            if re.fullmatch(r"(?:[a-zA-Z]\s?){2,}", palabra + " "):
                palabra = palabra.replace(" ", "")
            palabras_limpias.append(palabra)
        x = " ".join(palabras_limpias)

        return x

    # Aplicar limpieza general
    df = df.applymap(limpiar_celda)

    # Normalización de separadores solo en columnas específicas
    for col in columnas_con_separadores:
        if col in df.columns and df[col].dtype == object:
            df[col] = (
                df[col]
                .apply(lambda x: re.sub(r"[,\;/]+", ";", x) if isinstance(x, str) else x)
                .apply(lambda x: re.sub(r"\s*;\s*", ";", x) if isinstance(x, str) else x)
                .apply(lambda x: re.sub(r";+", ";", x) if isinstance(x, str) else x)
                .apply(lambda x: x.strip(";") if isinstance(x, str) else x)
            )

    # Capitalización personalizada
    for col in df.columns:
        if col in df.columns and df[col].dtype == object:
            if col == "nombre_cientifico":
                # Forzar a minúscula completa
                df[col] = df[col].apply(lambda x: x.lower() if isinstance(x, str) else x)
            else:
                # Capitaliza solo la primera letra de cada parte separada por ";"
                df[col] = df[col].apply(
                    lambda x: ";".join(
                        parte.strip().capitalize()
                        for parte in x.split(";")
                    ) if isinstance(x, str) else x
                )

    return df



# --- Archivos Excel ---
archivos = {
    "Tablas_Bosquimanxs.xlsx": "data/Tablas_Bosquimanxs.xlsx",
    "103_plantas_medicinales.xlsx": "data/103_plantas_medicinales.xlsx",
    "calendario_siembra_completo_zona_central.xlsx": "data/calendario_siembra_completo_zona_central.xlsx",
    "registros_aucca_mau.xlsx": "data/registros_aucca_mau.xlsx"
}


fuente_informacion = {
    "Tablas_Bosquimanxs.xlsx": "Bosquimanxs (2017) Bosquímanos. Una guía para la regeneración de los tejidos de la tierra. Cimarrón Subversiones. Tralkawenu, Lafken Mapu ",
    "103_plantas_medicinales.xlsx": "FUCOA (2018) 03 Hierbas Medicinales. Santiago, Chile: ",
    "calendario_siembra_completo_zona_central.xlsx": "Fundación Ilumina (2017) Manual Programa Naturalizar Educativamente. Santiago de Chile  ",
    "registros_aucca_mau.xlsx": "Aucca (2025) registros de nombres científicos"
}



tablas_cargadas = {}

for nombre_archivo, ruta in archivos.items():
    try:
        xls = pd.ExcelFile(ruta)
        fuente = fuente_informacion.get(nombre_archivo, nombre_archivo)  # busca fuente completa
        for hoja in xls.sheet_names:
            try:
                df = pd.read_excel(xls, sheet_name=hoja)
                df_limpio = limpiar_dataframe(df)
                df_limpio["fuente"] = f"{fuente} (Hoja: {hoja})"
                key = f"{nombre_archivo} / {hoja}"
                tablas_cargadas[key] = df_limpio
            except Exception as e:
                st.warning(f"⚠️ Error leyendo hoja '{hoja}' en archivo '{nombre_archivo}': {e}")
    except Exception as e:
        st.error(f"❌ No se pudo abrir el archivo {nombre_archivo}: {e}")




# --- Mapeo nombre_comun → nombre_cientifico ---
pares = []
for df in tablas_cargadas.values():
    if "nombre_cientifico" in df.columns and "nombre_comun" in df.columns:
        for _, row in df[["nombre_cientifico", "nombre_comun"]].dropna().iterrows():
            for nombre in str(row["nombre_comun"]).split(";"):
                pares.append((nombre.strip().lower(), row["nombre_cientifico"].strip().lower()))
dicc_nombre_comun_a_cientifico = dict(pares)

for nombre_tabla, df in tablas_cargadas.items():
    if "nombre_cientifico" not in df.columns and "nombre_comun" in df.columns:
        df["nombre_cientifico"] = df["nombre_comun"].apply(
            lambda val: dicc_nombre_comun_a_cientifico.get(str(val).strip().lower(), None)
        )
        tablas_cargadas[nombre_tabla] = df

# --- Crear plantas_base (antes de exportar a SQLite) ---
nombres_cientificos_totales = set()
for df in list(tablas_cargadas.values()):
    if "nombre_cientifico" in df.columns:
        nombres_cientificos_totales.update(df["nombre_cientifico"].dropna().unique())
nombres_cientificos_totales = sorted(nombres_cientificos_totales)

grupo_id = 1
grupos = {}
asignados = set()
for nombre in nombres_cientificos_totales:
    if nombre in asignados:
        continue
    grupo = [nombre]
    asignados.add(nombre)
    for otro in nombres_cientificos_totales:
        if otro in asignados:
            continue
        if fuzz.token_sort_ratio(nombre, otro) >= 90:
            grupo.append(otro)
            asignados.add(otro)
    for g in grupo:
        grupos[g] = {
            "id_planta": f"P{grupo_id:04}",
            "nombre_estandarizado": nombre
        }
    grupo_id += 1

plantas_base = pd.DataFrame([
    {
        "id_planta": info["id_planta"],
        "nombre_cientifico": nombre,
        "nombre_estandarizado": info["nombre_estandarizado"]
    }
    for nombre, info in grupos.items()
])

# Agregar id_planta a todas las tablas cargadas
def agregar_id_planta(df):
    if "nombre_cientifico" in df.columns:
        df["id_planta"] = df["nombre_cientifico"].map(lambda x: grupos.get(x, {}).get("id_planta"))
    return df

tablas_cargadas = {k: agregar_id_planta(df.copy()) for k, df in tablas_cargadas.items()}

# --- Explosión de columnas relacionales ---
columnas_relacionales_por_tabla = {
    "Tablas_Bosquimanxs.xlsx / nombres":["nombre_comun"],
    "Tablas_Bosquimanxs.xlsx / frutales": ["nombre_comun","aporte nutricional"],
    "Tablas_Bosquimanxs.xlsx / fijadores_nitrogeno":["nombre_comun"],
    "Tablas_Bosquimanxs.xlsx / cobertura_suelo":["nombre_comun"],
    "Tablas_Bosquimanxs.xlsx / acumulador_dinamico":["nombre_comun"],
    "Tablas_Bosquimanxs.xlsx / plantas_confusoras_pestes":["nombre_comun"], 
    "103_plantas_medicinales.xlsx / plantas": ["efectos", "parte_utilizada"],
}

tablas_relacionales = {}
for nombre_tabla, columnas in columnas_relacionales_por_tabla.items():
    if nombre_tabla not in tablas_cargadas:
        continue
    df = tablas_cargadas[nombre_tabla]
    for col in columnas:
        if col in df.columns and "nombre_cientifico" in df.columns:
            df_relacional = df[["nombre_cientifico", col, "fuente"]].dropna().copy()
            df_relacional[col] = df_relacional[col].astype(str).str.split(";")
            df_relacional = df_relacional.explode(col)
            df_relacional[col] = df_relacional[col].str.strip().str.capitalize()
            df_relacional["id_planta"] = df_relacional["nombre_cientifico"].map(lambda x: grupos.get(x, {}).get("id_planta"))
            tabla_key = f"{nombre_tabla} → {col}"
            tablas_relacionales[tabla_key] = df_relacional.dropna().drop_duplicates()

# --- Exportar a SQLite ---
ruta_db = "db/base_plantas_agroecologia.sqlite"
conn = sqlite3.connect(ruta_db)

def limpiar_nombre_sql(nombre):
    return nombre.replace(".xlsx", "").replace(" / ", "__").replace(" → ", "__").replace(" ", "_").lower()

# Exportar plantas_base
plantas_base.to_sql("plantas_base", conn, if_exists="replace", index=False)

# Guardar todas las tablas
for tablas in [tablas_cargadas, tablas_relacionales]:
    for nombre_tabla, df in tablas.items():
        nombre_sql = limpiar_nombre_sql(nombre_tabla)
        df = df.loc[:, df.columns.notna()]
        df = df.loc[:, df.columns != ""]
        if df.empty or sum([len(str(col)) for col in df.columns if col]) == 0:
            continue
        try:
            df.to_sql(nombre_sql, conn, if_exists="replace", index=False)
        except Exception as e:
            st.error(f"❌ Error exportando tabla {nombre_sql}: {e}")

conn.close()
st.success(f"✅ Base de datos guardada en {ruta_db}")

# Mostrar tabla plantas_base
st.markdown("## 🌿 Tabla maestra: plantas_base")
st.dataframe(plantas_base, use_container_width=True)



# Ruta a tu archivo SQLite
# ruta_db = "base_plantas_agroecologia.sqlite"

# Conectar a la base de datos
conn = sqlite3.connect(ruta_db)

# Consulta para obtener los nombres de todas las tablas
query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"

try:
    # Ejecutar la consulta y cargar los resultados en un DataFrame
    tablas = pd.read_sql(query, conn)
    conn.close()

    # Mostrar las tablas en la aplicación Streamlit
    st.markdown("## 📋 Tablas disponibles en la base de datos")
    st.dataframe(tablas, use_container_width=True)
except Exception as e:
    st.error(f"❌ Error al listar las tablas en SQLite: {e}")





# st.title("🌱 Plantas que se siembran en mayo")
# st.sidebar.markdown("dd")



# # Ruta a tu base de datos
# #ruta_db = "base_plantas_agroecologia.sqlite"

# try:
#     conn = sqlite3.connect(ruta_db)
#     query = """
#         SELECT DISTINCT id_planta, nombre_cientifico, nombre_comun, `mes siembra`
#         FROM calendario_siembra_completo_zona_central__calendario
#         WHERE LOWER(`mes siembra`) LIKE '%mayo%'
#     """
#     df_mayo = pd.read_sql(query, conn)
#     conn.close()

#     if df_mayo.empty:
#         st.warning("⚠️ No se encontraron plantas para mayo.")
#     else:
#         st.success(f"✅ {len(df_mayo)} plantas encontradas para mayo:")
#         st.dataframe(df_mayo, use_container_width=True)
# except Exception as e:
#     st.error(f"❌ Error al consultar plantas de mayo: {e}")
 
 
 
 
 
    
# import sqlite3
# import pandas as pd
# import streamlit as st

# st.title("🔍 Ficha completa por planta")

# nombre_cientifico_objetivo = st.text_input("🔎 Ingresa el nombre científico:", "allium sativum").strip().lower()
# #ruta_db = "base_plantas_agroecologia.sqlite"

# if nombre_cientifico_objetivo:
#     try:
#         conn = sqlite3.connect(ruta_db)

#         # Obtener id_planta desde plantas_base
#         query_id = """
#             SELECT id_planta, nombre_cientifico, nombre_estandarizado
#             FROM plantas_base
#             WHERE LOWER(nombre_cientifico) = ?
#         """
#         df_id = pd.read_sql(query_id, conn, params=(nombre_cientifico_objetivo,))

#         if df_id.empty:
#             st.warning("⚠️ No se encontró una planta con ese nombre científico.")
#         else:
#             id_planta = df_id.iloc[0]["id_planta"]
#             st.success(f"✅ Planta encontrada: {id_planta}")
#             st.dataframe(df_id)

#             # Buscar en todas las tablas el contenido relacionado
#             tablas = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
#             tablas = tablas["name"].tolist()

#             for tabla in tablas:
#                 try:
#                     query = f"SELECT * FROM {tabla} WHERE id_planta = ?"
#                     df = pd.read_sql(query, conn, params=(id_planta,))
#                     if not df.empty:
#                         st.subheader(f"📄 Información desde: `{tabla}`")
#                         st.dataframe(df, use_container_width=True)
#                 except Exception as e:
#                     st.warning(f"No se pudo leer {tabla}: {e}")

#         conn.close()
#     except Exception as e:
#         st.error(f"❌ Error consultando la base de datos: {e}")
