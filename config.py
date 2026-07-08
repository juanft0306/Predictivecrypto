import os

# ============================================================
#  CREDENCIALES DE TELEGRAM (OBLIGATORIAS DESDE ENTORNO)
# ============================================================
TOKEN_TELEGRAM = os.environ.get("TOKEN_TELEGRAM")
CHAT_ID_TELEGRAM = os.environ.get("CHAT_ID_TELEGRAM")

# Validación estricta: si faltan, el programa no arranca.
if not TOKEN_TELEGRAM:
    raise EnvironmentError(
        "❌ La variable de entorno TOKEN_TELEGRAM no está definida.\n"
        "   Configúrala en Render o en tu archivo .env"
    )
if not CHAT_ID_TELEGRAM:
    raise EnvironmentError(
        "❌ La variable de entorno CHAT_ID_TELEGRAM no está definida.\n"
        "   Configúrala en Render o en tu archivo .env"
    )

# ============================================================
#  ALMACENAMIENTO CENTRAL EN MEMORIA (compartido entre módulos)
# ============================================================
datos_mercado = {
    "precio_actual": 0.0,
    "rsi": 50.0,
    "variacion": 0.0,
    "ultima_actualizacion": "N/A",
    "hora_venezuela": "--:--"
}

# Historial de análisis (máximo 5 entradas, se gestiona en bot.py)
historial_analisis = []
