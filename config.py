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
#  ALMACENAMIENTO DE DATOS DE MERCADO
# ============================================================
datos_mercado = {}
for moneda in MONEDAS:
    datos_mercado[moneda] = {
        "precio_actual": 0.0,
        "variacion": 0.0,
        "rsi": 50.0,
        "ultima_actualizacion": "N/A",
        "hora_venezuela": "--:--",
        "nombre": NOMBRES_MONEDAS.get(moneda, moneda),
        "capital_invertido": 0.0,
        "ganancia_deseada": 0.0,
        "monto_total_deseado": 0.0,
        "precio_objetivo": 0.0,
        "valor_actual_inversion": 0.0,
        "ganancia_actual": 0.0
    }

historial_analisis = []
actualizacion_event = threading.Event()

RSI_SOBREVENTA = 30
RSI_SOBRECOMPRA = 70
VARIACION_ALERTA = 5.0

# ============================================================
#  DATOS DE INVERSIÓN (NUEVA ESTRUCTURA)
# ============================================================
inversiones = {}
for moneda in MONEDAS:
    inversiones[moneda] = {
        "cantidad": 0.0,
        "capital_invertido": 0.0,   # Ahora lo ingresa el usuario
        "ganancia_deseada": 0.0,
        "alcanzado": False
    }

moneda_seleccionada = "BTCUSDT"
