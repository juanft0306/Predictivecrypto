import time
import requests
import config
from analisis import calcular_todos
from probabilidad import calcular_prob_subida
from recomendaciones import generar_recomendacion
from inversion import cargar, guardar, marcar_alcanzado
from utils import hora_ve, hora_utc

INTERVALO = 5

# Estados para evitar duplicados
ult_rsi = {}
ult_var = {}
ult_recom = {}
ult_prob = {}

for m in config.MONEDAS:
    ult_rsi[m] = None
    ult_var[m] = False
    ult_recom[m] = None
    ult_prob[m] = False

def enviar_telegram(mensaje):
    if not config.TOKEN_TELEGRAM or not config.CHAT_ID_TELEGRAM:
        return
    url = f"https://api.telegram.org/bot{config.TOKEN_TELEGRAM}/sendMessage"
    payload = {
        "chat_id": config.CHAT_ID_TELEGRAM,
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except:
        pass

def obtener_tickers():
    url = "https://api.binance.us/api/v3/ticker/24hr"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            tickers = {}
            for item in data:
                if item['symbol'] in config.MONEDAS:
                    tickers[item['symbol']] = {
                        "precio": float(item['lastPrice']),
                        "variacion": float(item['priceChangePercent'])
                    }
            return tickers
    except:
        pass
    return None

def obtener_velas(symbol, limit=200):
    url = f"https://api.binance.us/api/v3/klines?symbol={symbol}&interval=1d&limit={limit}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return [float(v[4]) for v in data]
    except:
        pass
    return None

def analizar():
    global ult_rsi, ult_var, ult_recom, ult_prob

    tickers = obtener_tickers()
    if not tickers:
        return

    ahora_ve = hora_ve()
    ahora_utc = hora_utc()

    inversiones = cargar()

    for symbol in config.MONEDAS:
        if symbol not in tickers:
            continue

        datos = tickers[symbol]
        precio = datos["precio"]
        variacion = datos["variacion"]

        precios = obtener_velas(symbol, 200)
        if not precios or len(precios) < 30:
            continue

        ind = calcular_todos(precios)
        prob_subida = calcular_prob_subida(precios)
        prob_bajada = 100 - prob_subida
        recom, color, emoji = generar_recomendacion(ind, prob_subida, precio)

        config.datos_mercado[symbol].update({
            "precio_actual": precio,
            "variacion": variacion,
            "rsi": ind["rsi"],
            "prob_subida": prob_subida,
            "prob_bajada": prob_bajada,
            "recomendacion": recom,
            "ultima_actualizacion": ahora_utc,
            "hora_venezuela": ahora_ve
        })

        # ALERTAS

        # 1. Variación brusca
        if abs(variacion) >= config.VARIACION_ALERTA and not ult_var[symbol]:
            signo = "+" if variacion >= 0 else ""
            msg = f"[📊 DASHBOARD] *{config.NOMBRES.get(symbol, symbol)} ({symbol.replace('USDT','')})*\n💰 ${precio:,.2f}\n📈 {signo}{variacion:.2f}%\n🕒 {ahora_ve}"
            enviar_telegram(msg)
            ult_var[symbol] = True
        elif abs(variacion) < config.VARIACION_ALERTA:
            ult_var[symbol] = False

        # 2. RSI
        estado = "Neutral"
        if ind["rsi"] < config.RSI_SOBREVENTA:
            estado = "Sobrevendido"
        elif ind["rsi"] > config.RSI_SOBRECOMPRA:
            estado = "Sobrecomprado"

        if estado != "Neutral" and ult_rsi[symbol] != estado:
            emoji_rsi = "🔴" if estado == "Sobrevendido" else "🟢"
            msg = f"[📊 DASHBOARD] {emoji_rsi} *{config.NOMBRES.get(symbol, symbol)}*\n📊 RSI: {ind['rsi']:.2f} ({estado})\n💰 ${precio:,.2f}\n🕒 {ahora_ve}"
            enviar_telegram(msg)
            ult_rsi[symbol] = estado
        elif estado == "Neutral":
            ult_rsi[symbol] = None

        # 3. Recomendación
        if recom != ult_recom[symbol]:
            msg = f"[💡 CONSEJO] *{config.NOMBRES.get(symbol, symbol)}*\n📊 {emoji} {recom}\n📈 Subida: {prob_subida:.1f}% | 📉 Bajada: {prob_bajada:.1f}%\n💰 ${precio:,.2f}\n🕒 {ahora_ve}"
            enviar_telegram(msg)
            ult_recom[symbol] = recom

        # 4. Probabilidad extrema
        if prob_subida >= config.PROB_ALERTA and not ult_prob[symbol]:
            msg = f"[💡 SEÑAL FUERTE] *{config.NOMBRES.get(symbol, symbol)}*\n🚀 Prob. Subida: {prob_subida:.1f}%\n📊 {recom}\n💰 ${precio:,.2f}\n🕒 {ahora_ve}"
            enviar_telegram(msg)
            ult_prob[symbol] = True
        elif prob_bajada >= config.PROB_ALERTA and not ult_prob[symbol]:
            msg = f"[💡 SEÑAL FUERTE] *{config.NOMBRES.get(symbol, symbol)}*\n🔻 Prob. Bajada: {prob_bajada:.1f}%\n📊 {recom}\n💰 ${precio:,.2f}\n🕒 {ahora_ve}"
            enviar_telegram(msg)
            ult_prob[symbol] = True
        elif prob_subida < 70 and prob_bajada < 70:
            ult_prob[symbol] = False

        # 5. Inversión: meta alcanzada
        inv = inversiones.get(symbol, {})
        if inv.get("cantidad", 0) > 0 and inv.get("capital", 0) > 0 and inv.get("ganancia_deseada", 0) > 0:
            capital = inv["capital"]
            ganancia_deseada = inv["ganancia_deseada"]
            cantidad = inv["cantidad"]
            valor_actual = cantidad * precio
            meta = capital + ganancia_deseada

            if valor_actual >= meta and not inv.get("alcanzado", False):
                ganancia_real = ((valor_actual - capital) / capital) * 100
                msg = f"[💰 INVERSIÓN] 🎯 *¡META ALCANZADA en {config.NOMBRES.get(symbol, symbol)}!*\n💰 Capital: ${capital:,.2f}\n🎯 Ganancia deseada: ${ganancia_deseada:,.2f}\n💵 Valor actual: ${valor_actual:,.2f}\n📈 Ganancia: {ganancia_real:+.2f}%\n🕒 {ahora_ve}"
                enviar_telegram(msg)
                marcar_alcanzado(symbol)

    # Historial de precios para gráficos
    moneda_sel = config.moneda_seleccionada if hasattr(config, 'moneda_seleccionada') else "BTCUSDT"
    if moneda_sel in config.datos_mercado:
        precio_sel = config.datos_mercado[moneda_sel]["precio_actual"]
        rsi_sel = config.datos_mercado[moneda_sel]["rsi"]
        config.historial_precios.append({
            "fecha": ahora_ve,
            "precio": precio_sel,
            "rsi": rsi_sel
        })
        if len(config.historial_precios) > 100:
            config.historial_precios.pop(0)

    config.actualizacion_event.set()
    config.logger.info(f"Datos actualizados para {len(config.MONEDAS)} monedas")

def bucle():
    config.logger.info("🤖 Bot iniciado")
    while True:
        try:
            analizar()
        except Exception as e:
            config.logger.error(f"Error: {e}")
        time.sleep(INTERVALO)
