from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx
import os

load_dotenv()

app = FastAPI(title="Casita de Semillas - API Híbrida", version="1.0")

# --- CONFIGURACION INICIAL ---
TREFLE_API_KEY = os.getenv("TREFLE_API_KEY")
TREFLE_API_BASE = "https://trefle.io/api/v1"
AGROECO_API_BASE = "127.0.0.1:5000/  # reemplaza con tu URL publicada o local

# --- MODELOS DE RESPUESTA ---
class FuenteResultado(BaseModel):
    fuente: str
    datos: dict

class RespuestaUnificada(BaseModel):
    nombre_consultado: str
    resultados: list[FuenteResultado]


# --- ENDPOINT PRINCIPAL ---
@app.get("/buscar/{nombre}", response_model=RespuestaUnificada)
async def buscar_planta(nombre: str):
    resultados = []

    # 1. Consultar API Agroecológica local
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{AGROECO_API_BASE}/resolver_nombre_comun/{nombre}")
            if r.status_code == 200:
                resultados.append({
                    "fuente": "agroecologia_local",
                    "datos": r.json()
                })
            else:
                resultados.append({"fuente": "agroecologia_local", "datos": {"status": r.status_code}})
    except Exception as e:
        resultados.append({"fuente": "agroecologia_local", "datos": {"error": str(e)}})

    # 2. Consultar Trefle API
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{TREFLE_API_BASE}/plants/search",
                params={"q": nombre, "token": TREFLE_API_KEY}
            )
            if r.status_code == 200:
                resultados.append({
                    "fuente": "trefle",
                    "datos": r.json()
                })
            else:
                resultados.append({"fuente": "trefle", "datos": {"status": r.status_code}})
    except Exception as e:
        resultados.append({"fuente": "trefle", "datos": {"error": str(e)}})

    # 3. (Futuro) Consulta a Plant.id podría ir aquí
    # ...

    return {
        "nombre_consultado": nombre,
        "resultados": resultados
    }
