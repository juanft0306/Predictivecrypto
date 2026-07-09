def generar_recomendacion(ind, prob_subida, precio):
    rsi = ind["rsi"]
    macd = ind["macd"]
    senal = ind["senal"]
    sma7 = ind["sma7"]
    sma25 = ind["sma25"]
    golden = ind["golden"]
    death = ind["death"]

    buy = 0
    sell = 0
    total = 6

    if rsi < 30: buy += 1
    elif rsi > 70: sell += 1
    if macd > senal: buy += 1
    else: sell += 1
    if precio <= ind["banda_inf"]: buy += 1
    elif precio >= ind["banda_sup"]: sell += 1
    if precio > sma7: buy += 1
    else: sell += 1
    if precio > sma25: buy += 1
    else: sell += 1
    if golden: buy += 1
    elif death: sell += 1

    buy_ratio = buy / total
    sell_ratio = sell / total

    if buy_ratio >= 0.83:
        return "COMPRA FUERTE", "verde", "🟢"
    elif buy_ratio >= 0.67:
        return "COMPRA", "verde_claro", "✅"
    elif buy_ratio >= 0.50 and sell_ratio <= 0.33:
        return "COMPRA LIGERA", "verde_oscuro", "📈"
    elif sell_ratio >= 0.83:
        return "VENTA FUERTE", "rojo", "🔴"
    elif sell_ratio >= 0.67:
        return "VENTA", "naranja", "⚠️"
    elif sell_ratio >= 0.50 and buy_ratio <= 0.33:
        return "VENTA LIGERA", "amarillo", "📉"
    else:
        return "MANTENER", "azul", "⏸️"
