from datetime import datetime
import config

def hora_ve():
    return datetime.now(config.ZONA_VE).strftime("%I:%M:%S %p")

def hora_utc():
    return datetime.utcnow().strftime("%H:%M:%S UTC")

def fmt_num(valor, dec=2):
    return f"{valor:,.{dec}f}"

def redondear(valor, dec=2):
    return round(valor, dec)
