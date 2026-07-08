import os
import threading
import logging
from zoneinfo import ZoneInfo

# ============================================================
#  LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================
#  CREDENCIALES DE TELEGRAM
# ============================================================
TOKEN_TELEGRAM = os.environ.get("TOKEN_TELEGRAM")
CHAT_ID_TELEGRAM = os.environ.get("CHAT_ID_TELEGRAM")

if not TOKEN_TELEGRAM:
    raise EnvironmentError("❌ Falta TOKEN_TELEGRAM en variables de entorno")
if not CHAT_ID_TELEGRAM:
    raise EnvironmentError("❌ Falta CHAT_ID_TELEGRAM en variables de entorno")

# ============================================================
#  ZONA HORARIA
# ============================================================
ZONA_VE = ZoneInfo("America/Caracas")

# ============================================================
#  DATOS DE MERCADO (compartidos)
# ============================================================
datos_mercado = {
    "precio_actual": 0.0,
    "rsi": 50.0,
    "variacion": 0.0,
    "ultima_actualizacion": "N/A",
    "hora_venezuela": "--:--",
    # Campos de inversión
    "cantidad_btc": 0.0,
    "precio_objetivo": 0.0,
    "valor_inversion": 0.0,
    "ganancia_perdida": 0.0
}

historial_analisis = []   # Máximo 5 entradas

# Evento SSE
actualizacion_event = threading.Event()

# Umbrales de alerta
RSI_SOBREVENTA = 30
RSI_SOBRECOMPRA = 70
VARIACION_ALERTA = 5.0

# ============================================================
#  DATOS DE INVERSIÓN (persistencia en memoria)
# ============================================================
cantidad_btc = 0.0
precio_objetivo = 0.0
objetivo_alcanzado = False   # Evita notificaciones duplicadas
