import os

# === CREDENCIALES DE TELEGRAM ===
TOKEN_TELEGRAM = os.environ.get(
    "TOKEN_TELEGRAM", "8113503204:AAF54TCwgjngtCyhYvWbCxDLMfyTrfTOB8"
)
CHAT_ID_TELEGRAM = os.environ.get("CHAT_ID_TELEGRAM", "5997657424")

# === ESTRUCTURAS DE DATOS EN MEMORIA ===
# Al estar en un archivo central, Flask y el Bot pueden leerlos/escribirlos sin interferir en sus flujos principales
datos_mercado = {"precio_actual": 0.0, "rsi": 50.0, "ultima_actualizacion": "N/A"}

historial_analisis = []  # Guarda los últimos 10 análisis realizados
