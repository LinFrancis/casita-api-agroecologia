import streamlit as st
import requests

st.set_page_config(page_title="🌿 Explorador Casita de Semillas", layout="wide")
st.title("🌱 Explorador de Plantas Agroecológicas")

API_BASE = "https://casita-api-agroecologia.onrender.com"

# --- Búsqueda por nombre común o científico ---
nombre = st.text_input("🔍 Buscar por nombre común o científico:", "")

if nombre:
    st.subheader("📋 Resultados encontrados")
    url = f"{API_BASE}/resolver_nombre_comun/{nombre}"
    response = requests.get(url)

    st.write("🔧 Debug:")
    st.code(f"URL consultada: {url}")
    st.code(f"Status: {response.status_code}")

    try:
        datos = response.json()
        st.json(datos)

        if response.status_code == 200 and isinstance(datos, list) and len(datos) > 0:
            opciones = [f"{d['nombre_comun']} → {d['nombre_cientifico']} (ID: {d['id_planta']})" for d in datos]
            seleccion = st.selectbox("Selecciona una planta:", opciones)

            id_planta = seleccion.split("ID: ")[-1].replace(")", "")

            st.subheader("📘 Ficha completa")
            ficha = requests.get(f"{API_BASE}/ficha_completa/{id_planta}").json()

            for tabla, registros in ficha.get("datos", {}).items():
                st.markdown(f"### 🗂 {tabla}")
                if isinstance(registros, list):
                    for i, r in enumerate(registros):
                        with st.expander(f"🔸 Registro {i+1}"):
                            st.json(r)
                else:
                    st.json(registros)
        else:
            st.warning("⚠️ No se encontraron coincidencias.")

    except Exception as e:
        st.error(f"❌ No se pudo decodificar la respuesta: {e}")

st.markdown("---")
st.caption("Casita de Semillas 🌾 • Explorador conectado a API agroecológica en Render")
