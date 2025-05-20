import streamlit as st
import pandas as pd
import re

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





# Archivos y rutas
archivos = {
    "Tablas_Bosquimanxs.xlsx": "data/Tablas_Bosquimanxs.xlsx",
    "103_plantas_medicinales.xlsx": "data/103_plantas_medicinales.xlsx",
    "calendario_siembra_completo_zona_central.xlsx": "data/calendario_siembra_completo_zona_central.xlsx",
    "registros_aucca_mau.xlsx": "data/registros_aucca_mau.xlsx"
}

# Cargar y limpiar todas las hojas de todos los archivos
tablas_cargadas = {}
for nombre_archivo, ruta in archivos.items():
    try:
        xls = pd.ExcelFile(ruta)
        for hoja in xls.sheet_names:
            try:
                df = pd.read_excel(xls, sheet_name=hoja)
                df_limpio = limpiar_dataframe(df)
                key = f"{nombre_archivo} / {hoja}"
                tablas_cargadas[key] = df_limpio
            except Exception as e:
                st.warning(f"⚠️ Error leyendo hoja '{hoja}' en archivo '{nombre_archivo}': {e}")
    except Exception as e:
        st.error(f"❌ No se pudo abrir el archivo {nombre_archivo}: {e}")


# Paso 1: Crear mapeo nombre_comun → nombre_cientifico
pares = []
for df in tablas_cargadas.values():
    if "nombre_cientifico" in df.columns and "nombre_comun" in df.columns:
        for _, row in df[["nombre_cientifico", "nombre_comun"]].dropna().iterrows():
            for nombre in str(row["nombre_comun"]).split(";"):
                pares.append((nombre.strip().lower(), row["nombre_cientifico"].strip().lower()))

dicc_nombre_comun_a_cientifico = dict(pares)

# Paso 2: Completar columnas faltantes
for nombre_tabla, df in tablas_cargadas.items():
    if "nombre_cientifico" not in df.columns and "nombre_comun" in df.columns:
        df["nombre_cientifico"] = df["nombre_comun"].apply(
            lambda val: dicc_nombre_comun_a_cientifico.get(str(val).strip().lower(), None)
        )
        tablas_cargadas[nombre_tabla] = df


# Diccionario con columnas a explotar por tabla
columnas_relacionales_por_tabla = {
    "Tablas_Bosquimanxs.xlsx / nombres":["nombre_comun"],
    "Tablas_Bosquimanxs.xlsx / frutales": ["nombre_comun","aporte nutricional"],
    "Tablas_Bosquimanxs.xlsx / fijadores_nitrogeno":["nombre_comun"],
    "Tablas_Bosquimanxs.xlsx / cobertura_suelo":["nombre_comun"],
    "Tablas_Bosquimanxs.xlsx / acumulador_dinamico":["nombre_comun"],
    "Tablas_Bosquimanxs.xlsx / plantas_confusoras_pestes":["nombre_comun"], 
    "103_plantas_medicinales.xlsx / plantas": ["efectos", "parte_utilizada"],
    
}

# Nuevas tablas relacionales
tablas_relacionales = {}

# Procesar cada tabla según las columnas relacionales indicadas
for nombre_tabla, columnas in columnas_relacionales_por_tabla.items():
    if nombre_tabla not in tablas_cargadas:
        continue
    df = tablas_cargadas[nombre_tabla]
    for col in columnas:
        if col in df.columns and "nombre_cientifico" in df.columns:
            df_relacional = df[["nombre_cientifico", col]].dropna().copy()
            df_relacional[col] = df_relacional[col].astype(str).str.split(";")
            df_relacional = df_relacional.explode(col)
            df_relacional[col] = df_relacional[col].str.strip().str.capitalize()
            tabla_key = f"{nombre_tabla} → {col}"
            tablas_relacionales[tabla_key] = df_relacional.dropna().drop_duplicates()



# Mostrar nuevas tablas relacionales
for nombre_tabla, df_rel in tablas_relacionales.items():
    st.subheader(f"🔗 Relacional: {nombre_tabla} ({len(df_rel)} filas)")
    st.dataframe(df_rel, use_container_width=True)


# Mostrar tablas en Streamlit
for nombre_tabla, df in tablas_cargadas.items():
    st.subheader(f"📄 {nombre_tabla} ({len(df)} filas)")
    st.dataframe(df, use_container_width=True)








import sqlite3

# Ruta a tu archivo SQLite
ruta_db = "base_plantas_agroecologia.sqlite"
conn = sqlite3.connect(ruta_db)

# Función para limpiar nombres de tabla para SQLite
def limpiar_nombre_sql(nombre):
    return (
        nombre.replace(".xlsx", "")
        .replace(" / ", "__")
        .replace(" → ", "__")
        .replace(" ", "_")
        .lower()
    )

# Guardar tablas base
for nombre_tabla, df in tablas_cargadas.items():
    nombre_sql = limpiar_nombre_sql(nombre_tabla)

    # Eliminar columnas sin nombre (ej. columnas vacías en Excel)
    df = df.loc[:, df.columns.notna()]
    df = df.loc[:, df.columns != ""]

    # Verifica que la tabla tenga columnas válidas
    if df.empty or sum([len(str(col)) for col in df.columns if col]) == 0:
        st.warning(f"⚠️ Tabla vacía o sin columnas: {nombre_tabla}")
        continue

    try:
        df.to_sql(nombre_sql, conn, if_exists="replace", index=False)
        st.success(f"✅ Tabla exportada: {nombre_sql}")
    except Exception as e:
        st.error(f"❌ Error exportando tabla {nombre_sql}: {e}")


# Guardar tablas relacionales
for nombre_tabla, df in tablas_relacionales.items():
    nombre_sql = limpiar_nombre_sql(nombre_tabla)

    df = df.loc[:, df.columns.notna()]
    df = df.loc[:, df.columns != ""]

    if df.empty or sum(len(col) for col in df.columns if isinstance(col, str)) == 0:
        st.warning(f"⚠️ Tabla relacional vacía o sin columnas: {nombre_tabla}")
        continue

    try:
        df.to_sql(nombre_sql, conn, if_exists="replace", index=False)
        st.success(f"✅ Relacional exportada: {nombre_sql}")
    except Exception as e:
        st.error(f"❌ Error exportando relacional {nombre_sql}: {e}")

for nombre_tabla, df in tablas_relacionales.items():
    nombre_sql = limpiar_nombre_sql(nombre_tabla)
    df.to_sql(nombre_sql, conn, if_exists="replace", index=False)


from rapidfuzz import fuzz



# === AGRUPAR NOMBRES SIMILARES Y CREAR id_planta ===

# 1. Recolectar todos los nombre_cientifico únicos
nombres_cientificos_totales = set()
for df in list(tablas_cargadas.values()) + list(tablas_relacionales.values()):
    if "nombre_cientifico" in df.columns:
        nombres_cientificos_totales.update(df["nombre_cientifico"].dropna().unique())
nombres_cientificos_totales = sorted(nombres_cientificos_totales)

# 2. Agrupar por similitud con RapidFuzz
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

# 3. Crear tabla maestra de plantas
plantas_base = pd.DataFrame([
    {
        "id_planta": info["id_planta"],
        "nombre_cientifico": nombre,
        "nombre_estandarizado": info["nombre_estandarizado"]
    }
    for nombre, info in grupos.items()
])

# 4. Agregar id_planta a todas las tablas cargadas
def agregar_id_planta(df):
    if "nombre_cientifico" in df.columns:
        df["id_planta"] = df["nombre_cientifico"].map(lambda x: grupos.get(x, {}).get("id_planta"))
    return df

tablas_cargadas = {k: agregar_id_planta(df.copy()) for k, df in tablas_cargadas.items()}
tablas_relacionales = {k: agregar_id_planta(df.copy()) for k, df in tablas_relacionales.items()}

# 5. Exportar tabla plantas_base
try:
    plantas_base.to_sql("plantas_base", conn, if_exists="replace", index=False)
    st.success("✅ Tabla 'plantas_base' exportada a SQLite")
except Exception as e:
    st.error(f"❌ Error exportando 'plantas_base': {e}")

try:
    conn = sqlite3.connect("base_agroecologia.sqlite")
    # Exportar la tabla maestra plantas_base si no existe
    try:
        plantas_base.to_sql("plantas_base", conn, if_exists="replace", index=False)
        st.success("✅ Tabla 'plantas_base' guardada en SQLite")
    except Exception as e:
        st.error(f"❌ Error al guardar 'plantas_base': {e}")

    df_sql = pd.read_sql("SELECT * FROM plantas_base", conn)
    conn.close()
    st.dataframe(df_sql, use_container_width=True)
except Exception as e:
    st.error(f"❌ No se pudo leer plantas_base desde SQLite: {e}")
    

conn.close()
st.success(f"✅ Base de datos guardada en {ruta_db}")





conn = sqlite3.connect(ruta_db)
st.markdown("## 📦 Tablas exportadas a SQLite")
try:
    tablas = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
    conn.close()
    st.dataframe(tablas, use_container_width=True)
except Exception as e:
    st.error(f"❌ Error al listar las tablas en SQLite: {e}")







st.markdown("## 🧬 Relación entre tablas y `id_planta`")

# Crear tabla de relaciones
relaciones = []

for nombre_tabla in list(tablas_cargadas.keys()) + list(tablas_relacionales.keys()):
    relaciones.append({
        "tabla": nombre_tabla,
        "usa_id_planta": "id_planta" in tablas_cargadas.get(nombre_tabla, pd.DataFrame()).columns
                         or "id_planta" in tablas_relacionales.get(nombre_tabla, pd.DataFrame()).columns
    })

df_relaciones = pd.DataFrame(relaciones)
df_relaciones["usa_id_planta"] = df_relaciones["usa_id_planta"].map({True: "✅ Sí", False: "❌ No"})

st.dataframe(df_relaciones, use_container_width=True)

st.markdown("## 🌿 Tabla maestra: plantas_base con `id_planta`")
st.dataframe(plantas_base, use_container_width=True)




import sqlite3

st.subheader("🔍 Tablas disponibles en SQLite")

try:
    conn = sqlite3.connect("base_agroecologia.sqlite")
    tablas = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table'", conn)
    conn.close()

    st.dataframe(tablas)
except Exception as e:
    st.error(f"❌ Error al leer tablas de la base de datos: {e}")

st.subheader("🌿 Plantas que se siembran en mayo (desde SQLite)")

