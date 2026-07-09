import os
import threading
import logging
from zoneinfo import ZoneInfo

# LOGGING
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# TELEGRAM (obligatorio desde variables de entorno)
TOKEN_TELEGRAM = os.environ.get("TOKEN_TELEGRAM")
CHAT_ID_TELEGRAM = os.environ.get("CHAT_ID_TELEGRAM")

if not TOKEN_TELEGRAM:
    raise EnvironmentError("❌ Falta TOKEN_TELEGRAM")
if not CHAT_ID_TELEGRAM:
    raise EnvironmentError("❌ Falta CHAT_ID_TELEGRAM")

# ZONA HORARIA (Venezuela)
ZONA_VE = ZoneInfo("America/Caracas")

# MONEDAS PREDETERMINADAS (el usuario puede añadir más vía interfaz)
MONEDAS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT",
    "XRPUSDT", "TRXUSDT", "ADAUSDT", "DOGEUSDT",
    "DOTUSDT", "LINKUSDT"
]

NOMBRES = {
    "BTCUSDT": "Bitcoin",
    "ETHUSDT": "Ethereum",
    "BNBUSDT": "BNB Chain",
    "SOLUSDT": "Solana",
    "XRPUSDT": "XRP",
    "TRXUSDT": "TRON",
    "ADAUSDT": "Cardano",
    "DOGEUSDT": "Dogecoin",
    "DOTUSDT": "Polkadot",
    "LINKUSDT": "Chainlink"
}

# DATOS DE MERCADO (se actualizan en tiempo real)
datos_mercado = {}
for m in MONEDAS:
    datos_mercado[m] = {
        "precio_actual": 0.0,
        "variacion": 0.0,
        "rsi": 50.0,
        "prob_subida": 50.0,
        "prob_bajada": 50.0,
        "recomendacion": "Neutral",
        "ultima_actualizacion": "N/A",
        "hora_venezuela": "--:--",
        "nombre": NOMBRES.get(m, m)
    }

historial_precios = []  # para gráficos

actualizacion_event = threading.Event()

# UMBRALES DE ALERTA
RSI_SOBREVENTA = 30
RSI_SOBRECOMPRA = 70
VARIACION_ALERTA = 5.0
PROB_ALERTA = 80.0
