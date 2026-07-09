import os
import json
import threading
import logging
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

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
    logger.warning("⚠️ TOKEN_TELEGRAM no configurado. Las alertas no funcionarán.")
if not CHAT_ID_TELEGRAM:
    logger.warning("⚠️ CHAT_ID_TELEGRAM no configurado. Las alertas no funcionarán.")

# ============================================================
#  ZONA HORARIA
# ============================================================
ZONA_VE = ZoneInfo("America/Caracas")

# ============================================================
#  LISTA DE MONEDAS
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
#  DATOS DE INVERSIÓN
# ============================================================
inversiones = {}
for moneda in MONEDAS:
    inversiones[moneda] = {
        "cantidad": 0.0,
        "capital_invertido": 0.0,
        "ganancia_deseada": 0.0,
        "alcanzado": False
    }

moneda_seleccionada = "BTCUSDT"

# ============================================================
#  PERSISTENCIA DE INVERSIONES
# ============================================================
INVERSIONES_FILE = "inversiones.json"

def cargar_inversiones():
    global inversiones
    if os.path.exists(INVERSIONES_FILE):
        try:
            with open(INVERSIONES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for moneda in MONEDAS:
                    if moneda in data:
                        inversiones[moneda].update(data[moneda])
            logger.info("✅ Inversiones cargadas desde inversiones.json")
        except Exception as e:
            logger.error(f"Error al cargar inversiones: {e}")
    else:
        logger.info("ℹ️ No se encontró inversiones.json, usando valores por defecto.")

def guardar_inversiones():
    try:
        with open(INVERSIONES_FILE, "w", encoding="utf-8") as f:
            json.dump(inversiones, f, indent=2, ensure_ascii=False)
        logger.debug("💾 Inversiones guardadas en inversiones.json")
    except Exception as e:
        logger.error(f"Error al guardar inversiones: {e}")

cargar_inversiones()

# ============================================================
#  RECOMENDACIONES (se llenan en bot.py)
# ============================================================
recomendaciones = {}
ultima_recomendacion_enviada = {}

# ============================================================
#  ASISTENTE - PREGUNTAS PENDIENTES
# ============================================================
PREGUNTAS_FILE = "preguntas_pendientes.json"

def cargar_preguntas_pendientes():
    if os.path.exists(PREGUNTAS_FILE):
        try:
            with open(PREGUNTAS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def guardar_pregunta_pendiente(pregunta, fecha):
    pendientes = cargar_preguntas_pendientes()
    pendientes.append({"pregunta": pregunta, "fecha": fecha, "respondida": False})
    try:
        with open(PREGUNTAS_FILE, "w", encoding="utf-8") as f:
            json.dump(pendientes, f, indent=2, ensure_ascii=False)
        logger.info(f"📝 Pregunta guardada: {pregunta[:50]}...")
    except Exception as e:
        logger.error(f"Error al guardar pregunta: {e}")
