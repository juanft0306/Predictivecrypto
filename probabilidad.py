from analisis import calcular_todos

def calcular_prob_subida(precios):
    if not precios or len(precios) < 30:
        return 50.0
    ind = calcular_todos(precios)
    precio = precios[-1]

    # Factores ponderados
    # RSI (25%)
    if ind["rsi"] < 30:
        f_rsi = 0.9
    elif ind["rsi"] < 40:
        f_rsi = 0.7
    elif ind["rsi"] < 60:
        f_rsi = 0.5
    elif ind["rsi"] < 70:
        f_rsi = 0.3
    else:
        f_rsi = 0.1

    # MACD (20%)
    f_macd = 0.8 if ind["macd"] > ind["senal"] else 0.2

    # Bollinger (15%)
    if precio <= ind["banda_inf"]:
        f_bol = 0.9
    elif precio >= ind["banda_sup"]:
        f_bol = 0.1
    else:
        rango = ind["banda_sup"] - ind["banda_inf"]
        f_bol = 0.5 if rango == 0 else 0.9 - ((precio - ind["banda_inf"]) / rango) * 0.8

    # SMA7 (15%)
    f_sma7 = 0.8 if precio > ind["sma7"] * 1.02 else 0.6 if precio > ind["sma7"] else 0.2

    # Golden/Death (15%)
    f_cross = 0.8 if ind["golden"] else 0.2 if ind["death"] else 0.5

    # Volumen (10%) - simplificado
    f_vol = 0.5

    prob = (
        0.25 * f_rsi +
        0.20 * f_macd +
        0.15 * f_bol +
        0.15 * f_sma7 +
        0.15 * f_cross +
        0.10 * f_vol
    ) * 100

    prob = max(5, min(95, prob))
    return round(prob, 1)
