import pandas as pd
import numpy as np

def calcular_rsi(precios, periodos=14):
    if len(precios) < periodos + 1:
        return 50.0
    df = pd.DataFrame({'close': precios})
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periodos).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periodos).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0

def calcular_macd(precios, fast=12, slow=26, signal=9):
    if len(precios) < slow:
        return 0.0, 0.0
    df = pd.DataFrame({'close': precios})
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    senal = macd.ewm(span=signal, adjust=False).mean()
    return float(macd.iloc[-1]), float(senal.iloc[-1])

def calcular_bollinger(precios, periodos=20, desv=2):
    if len(precios) < periodos:
        return 0.0, 0.0
    df = pd.DataFrame({'close': precios})
    sma = df['close'].rolling(window=periodos).mean()
    std = df['close'].rolling(window=periodos).std()
    sup = sma + (std * desv)
    inf = sma - (std * desv)
    return float(sup.iloc[-1]), float(inf.iloc[-1])

def calcular_sma(precios, periodos):
    if len(precios) < periodos:
        return precios[-1] if precios else 0.0
    return float(sum(precios[-periodos:]) / periodos)

def calcular_todos(precios):
    if not precios or len(precios) < 30:
        return {
            "rsi": 50.0,
            "macd": 0.0,
            "senal": 0.0,
            "banda_sup": 0.0,
            "banda_inf": 0.0,
            "sma7": 0.0,
            "sma25": 0.0,
            "sma50": 0.0,
            "sma200": 0.0,
            "golden": False,
            "death": False
        }
    sma7 = calcular_sma(precios, 7)
    sma25 = calcular_sma(precios, 25)
    sma50 = calcular_sma(precios, 50)
    sma200 = calcular_sma(precios, 200) if len(precios) >= 200 else sma50
    macd, senal = calcular_macd(precios)
    band_sup, band_inf = calcular_bollinger(precios)
    rsi = calcular_rsi(precios)
    golden = sma50 > sma200
    death = sma50 < sma200
    return {
        "rsi": rsi,
        "macd": macd,
        "senal": senal,
        "banda_sup": band_sup,
        "banda_inf": band_inf,
        "sma7": sma7,
        "sma25": sma25,
        "sma50": sma50,
        "sma200": sma200,
        "golden": golden,
        "death": death
    }
