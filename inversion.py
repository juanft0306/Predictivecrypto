import json
import os
from datetime import datetime, timedelta
import config

ARCHIVO = "data/inversiones.json"

def cargar():
    if not os.path.exists(ARCHIVO):
        return {}
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def guardar(data):
    os.makedirs(os.path.dirname(ARCHIVO), exist_ok=True)
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def inicializar():
    inv = cargar()
    for m in config.MONEDAS:
        if m not in inv:
            inv[m] = {
                "cantidad": 0.0,
                "capital": 0.0,
                "ganancia_deseada": 0.0,
                "creado": datetime.utcnow().isoformat(),
                "alcanzado": False,
                "alcanzado_en": None
            }
    guardar(inv)
    return inv

def actualizar(symbol, cantidad, capital, ganancia):
    inv = cargar()
    if symbol not in inv:
        inv[symbol] = {}
    inv[symbol].update({
        "cantidad": cantidad,
        "capital": capital,
        "ganancia_deseada": ganancia,
        "creado": datetime.utcnow().isoformat(),
        "alcanzado": False,
        "alcanzado_en": None
    })
    guardar(inv)
    return inv[symbol]

def limpiar(symbol):
    inv = cargar()
    if symbol in inv:
        inv[symbol] = {
            "cantidad": 0.0,
            "capital": 0.0,
            "ganancia_deseada": 0.0,
            "creado": datetime.utcnow().isoformat(),
            "alcanzado": False,
            "alcanzado_en": None
        }
        guardar(inv)

def marcar_alcanzado(symbol):
    inv = cargar()
    if symbol in inv:
        inv[symbol]["alcanzado"] = True
        inv[symbol]["alcanzado_en"] = datetime.utcnow().isoformat()
        guardar(inv)

def obtener_historial():
    """
    Retorna lista de inversiones activas y alcanzadas.
    Las inversiones con más de 3 días de alcanzadas se eliminan automáticamente.
    """
    inv = cargar()
    ahora = datetime.utcnow()
    limite = timedelta(days=3)
    cambios = False

    for symbol, data in list(inv.items()):
        if data.get("alcanzado", False) and data.get("alcanzado_en"):
            fecha_alcanzado = datetime.fromisoformat(data["alcanzado_en"])
            if ahora - fecha_alcanzado > limite:
                del inv[symbol]
                cambios = True

    if cambios:
        guardar(inv)

    # Devolver solo las que tienen cantidad > 0
    return {k: v for k, v in inv.items() if v.get("cantidad", 0) > 0}
