import os
import threading

# ============================================================
#  CREDENCIALES DE TELEGRAM (OBLIGATORIAS DESDE ENTORNO)
# ============================================================
TOKEN_TELEGRAM = os.environ.get("TOKEN_TELEGRAM")
CHAT_ID_TELEGRAM = os.environ.get("CHAT_ID_TELEGRAM")

if not TOKEN_TELEGRAM:
    raise EnvironmentError("❌ Falta TOKEN_TELEGRAM en variables de entorno")
if not CHAT_ID_TELEGRAM:
    raise EnvironmentError("❌ Falta CHAT_ID_TELEGRAM en variables de entorno")

# ============================================================
#  ALMACENAMIENTO CENTRAL EN MEMORIA
# ============================================================
datos_mercado = {
    "precio_actual": 0.0,
    "rsi": 50.0,
    "variacion": 0.0,
    "ultima_actualizacion": "N/A",
    "hora_venezuela": "--:--"
}

historial_analisis = []   # Máximo 5 entradas (se controla en bot.py)

# Evento para notificar cambios (usado en SSE)
actualizacion_event = threading.Event()
