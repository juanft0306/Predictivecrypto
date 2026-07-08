import os

# === CREDENCIALES DE TELEGRAM ===
# Se leen de Render de forma segura. Se dejan tus datos actuales como respaldo.
TOKEN_TELEGRAM = os.environ.get(
    "TOKEN_TELEGRAM", "8113503204:AAF54TCwgjngtCyhYvWbCxDLMfyTrfTOB8"
)
CHAT_ID_TELEGRAM = os.environ.get("CHAT_ID_TELEGRAM", "5997657424")

# === ALMACENAMIENTO CENTRAL EN MEMORIA ===
datos_mercado = {"precio_actual": 0.0, "rsi": 50.0, "ultima_actualizacion": "N/A"}

historial_analisis = []  # Guarda los últimos 10 análisis realizados
