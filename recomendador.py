import config
import logging

logger = logging.getLogger(__name__)

def calcular_ema(precios, periodo):
    if len(precios) < periodo:
        return None
    k = 2 / (periodo + 1)
    ema = precios[0]
    for precio in precios[1:]:
        ema = precio * k + ema * (1 - k)
    return ema

def calcular_sma(precios, periodo):
    if len(precios) < periodo:
        return None
    return sum(precios[-periodo:]) / periodo

def calcular_rsi(precios, periodo=14):
    if len(precios) < periodo + 1:
        return 50.0
    cambios = [precios[i] - precios[i-1] for i in range(1, len(precios))]
    cambios_recientes = cambios[-periodo:]
    ganancias = sum(c for c in cambios_recientes if c > 0) / periodo
    perdidas = sum(abs(c) for c in cambios_recientes if c < 0) / periodo
    if perdidas == 0:
        return 100.0
    rs = ganancias / perdidas
    return 100 - (100 / (1 + rs))

def calcular_recomendacion(symbol, precio_actual, precios_historicos, variacion_24h=0):
    """
    Retorna recomendación con probabilidad y indicadores.
    NUNCA recomienda VENDER en pérdida (solo si el precio está por encima de su compra).
    Para simplificar, en este sistema no tenemos precio de compra por moneda,
    así que usamos la SMA50 como referencia de "precio justo".
    """
    if not precios_historicos or len(precios_historicos) < 50:
        return {
            "recomendacion": "Datos insuficientes",
            "probabilidad": 50,
            "indicadores": {"error": "No hay suficientes velas históricas"}
        }
    
    rsi = calcular_rsi(precios_historicos, 14)
    sma20 = calcular_sma(precios_historicos, 20) or precio_actual
    sma50 = calcular_sma(precios_historicos, 50) or precio_actual
    
    señales = []
    
    # RSI
    if rsi < 30:
        señales.append(("RSI sobrevendido", 0.9))
    elif rsi > 70:
        señales.append(("RSI sobrecomprado", -0.9))
    else:
        señales.append(("RSI neutral", 0))
    
    # Precio vs SMAs
    if precio_actual > sma20 and precio_actual > sma50:
        señales.append(("Precio por encima de SMAs", 0.6))
    elif precio_actual < sma20 and precio_actual < sma50:
        señales.append(("Precio por debajo de SMAs", -0.6))
    else:
        señales.append(("Precio entre SMAs", 0))
    
    # Cruce de SMAs
    if sma20 > sma50:
        señales.append(("SMA20 > SMA50 (alcista)", 0.4))
    elif sma20 < sma50:
        señales.append(("SMA20 < SMA50 (bajista)", -0.4))
    
    # MACD simplificado (usamos la tendencia de precio vs SMA50 como proxy)
    if precio_actual > sma50 and variacion_24h > 0:
        señales.append(("MACD alcista", 0.5))
    elif precio_actual < sma50 and variacion_24h < 0:
        señales.append(("MACD bajista", -0.5))
    
    # Variación 24h
    if variacion_24h > 3:
        señales.append(("Fuerte subida 24h", 0.3))
    elif variacion_24h < -3:
        señales.append(("Fuerte bajada 24h", -0.3))
    
    # Puntuación
    puntuacion = sum(peso for _, peso in señales)
    puntuacion = max(-1, min(1, puntuacion))
    probabilidad = int(((puntuacion + 1) / 2) * 100)
    
    # REGLA: NUNCA VENDER EN PÉRDIDA (usamos SMA50 como referencia de precio de compra)
    # Si el precio actual está por debajo de la SMA50, no recomendamos Vender
    if precio_actual < sma50 and probabilidad <= 30:
        recomendacion = "Mantener"  # Forzamos a Mantener en lugar de Vender
        probabilidad = 40  # Ajustamos la probabilidad para reflejar cautela
    elif probabilidad >= 70:
        recomendacion = "Comprar"
    elif probabilidad <= 30:
        recomendacion = "Vender"
    else:
        recomendacion = "Mantener"
    
    return {
        "recomendacion": recomendacion,
        "probabilidad": probabilidad,
        "indicadores": {
            "rsi": round(rsi, 2),
            "sma20": round(sma20, 2),
            "sma50": round(sma50, 2),
            "precio": round(precio_actual, 2),
            "variacion": round(variacion_24h, 2)
        }
    }
