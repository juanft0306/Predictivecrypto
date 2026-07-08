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
#  LISTA DE MONEDAS A SEGUIR
# ============================================================
MONEDAS = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "TRXUSDT"
]

NOMBRES_MONEDAS = {
    "BTCUSDT": "Bitcoin",
    "ETHUSDT": "Ethereum",
    "BNBUSDT": "BNB Chain",
    "SOLUSDT": "Solana",
    "XRPUSDT": "XRP",
    "TRXUSDT": "TRON"
}

# ============================================================
#  ALMACENAMIENTO DE DATOS DE MERCADO (por moneda)
# ============================================================
datos_mercado = {}
for moneda in MONEDAS:
    datos_mercado[moneda] = {
        "precio_actual": 0.0,
        "variacion": 0.0,
        "rsi": 50.0,
        "ultima_actualizacion": "N/A",
        "hora_venezuela": "--:--",
        "nombre": NOMBRES_MONEDAS.get(moneda, moneda)
    }

# Historial de análisis (solo para la moneda seleccionada en inversión)
historial_analisis = []   # Máximo 5 entradas

# Evento SSE
actualizacion_event = threading.Event()

# Umbrales de alerta
RSI_SOBREVENTA = 30
RSI_SOBRECOMPRA = 70
VARIACION_ALERTA = 5.0   # porcentaje

# ============================================================
#  DATOS DE INVERSIÓN (por moneda)
# ============================================================
inversiones = {}
for moneda in MONEDAS:
    inversiones[moneda] = {
        "cantidad": 0.0,
        "objetivo": 0.0,
        "alcanzado": False
    }

# Moneda seleccionada actualmente en la página de inversión
moneda_seleccionada = "BTCUSDT"
