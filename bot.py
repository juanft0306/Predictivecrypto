from datetime import datetime
import time
import requests
import config
from recomendador import calcular_recomendacion

HISTORIAL_MAX = 5
INTERVALO_ACTUALIZACION = 10

ultimo_estado_rsi = {}
ultima_variacion_alerta = {}

for moneda in config.MONEDAS:
    ultimo_estado_rsi[moneda] = None
    ultima_variacion_alerta[moneda] = False

def enviar_alerta_telegram(mensaje):
    if not config.TOKEN_TELEGRAM or not config.CHAT_ID_TELEGRAM:
        config.logger.warning("Credenciales de Telegram no configuradas.")
        return
    url = f"https://api.telegram.org/bot{config.TOKEN_TELEGRAM}/sendMessage"
    payload = {
        "chat_id": config.CHAT_ID_TELEGRAM,
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    try:
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code != 200:
            config.logger.error(f"Error al enviar alerta: {resp.text}")
    except Exception as e:
        config.logger.error(f"Excepción al enviar alerta: {e}")

def enviar_recomendacion_telegram(symbol, rec):
    if not config.TOKEN_TELEGRAM or not config.CHAT_ID_TELEGRAM:
        return
    nombre = config.NOMBRES_MONEDAS.get(symbol, symbol)
    abrev = symbol.replace('USDT', '')
    recomendacion = rec.get("recomendacion", "Mantener")
    probabilidad = rec.get("probabilidad", 50)
    indicadores = rec.get("indicadores", {})
    precio = indicadores.get("precio", 0)
    rsi = indicadores.get("rsi", "--")
    variacion = indicadores.get("variacion", 0)
    
    if recomendacion == "Comprar":
        emoji = "🟢"
        titulo = "SEÑAL DE COMPRA"
    elif recomendacion == "Vender":
        emoji = "🔴"
        titulo = "SEÑAL DE VENTA"
    else:
        emoji = "🟡"
        titulo = "RECOMENDACIÓN NEUTRAL"
    
    barras = "█" * int(probabilidad / 10) + "░" * (10 - int(probabilidad / 10))
    
    mensaje = (
        f"{emoji} *{titulo}* - {nombre} ({abrev})\n"
        f"📊 *Recomendación:* {recomendacion}\n"
        f"🎯 *Probabilidad:* {probabilidad}% {barras}\n"
        f"💰 *Precio actual:* ${precio:,.2f}\n"
        f"📈 *RSI (14):* {rsi}\n"
        f"📉 *Variación 24h:* {variacion:+.2f}%\n"
        f"📊 *SMA20:* ${indicadores.get('sma20', '--')} | *SMA50:* ${indicadores.get('sma50', '--')}\n"
        f"🕒 Hora local: {datetime.now(config.ZONA_VE).strftime('%I:%M:%S %p')}"
    )
    enviar_alerta_telegram(mensaje)

def obtener_todos_los_tickers():
    url = "https://api.binance.us/api/v3/ticker/24hr"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            tickers = {}
            for item in data:
                symbol = item['symbol']
                if symbol in config.MONEDAS:
                    tickers[symbol] = {
                        "lastPrice": float(item['lastPrice']),
                        "priceChangePercent": float(item['priceChangePercent'])
                    }
            return tickers
        else:
            config.logger.warning(f"Ticker 24h respondió con código {resp.status_code}")
    except Exception as e:
        config.logger.error(f"Error en ticker 24h: {e}")
    return None

def obtener_velas(symbol):
    endpoints = [
        f"https://api.binance.us/api/v3/klines?symbol={symbol}&interval=1d&limit=60",
        f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval=1d&limit=60"
    ]
    for url in endpoints:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                datos = resp.json()
                if len(datos) >= 2:
                    return [float(dia[4]) for dia in datos]
                else:
                    config.logger.warning(f"{url} devolvió solo {len(datos)} velas.")
            else:
                config.logger.warning(f"{url} respondió con código {resp.status_code}")
        except Exception as e:
            config.logger.error(f"Error en {url}: {e}")
    return None

def analizar_mercado():
    global ultimo_estado_rsi, ultima_variacion_alerta

    tickers = obtener_todos_los_tickers()
    if not tickers:
        config.logger.error("No se obtuvieron tickers de Binance.")
        return

    ahora_ve = datetime.now(config.ZONA_VE).strftime("%I:%M:%S %p")
    hora_utc = datetime.utcnow().strftime("%H:%M:%S UTC")

    for symbol in config.MONEDAS:
        if symbol not in tickers:
            config.logger.warning(f"No hay datos para {symbol}, se salta.")
            continue

        ticker = tickers[symbol]
        precio = ticker["lastPrice"]
        variacion = ticker["priceChangePercent"]

        precios = obtener_velas(symbol)
        rsi = calcular_rsi_precios(precios) if precios else 50.0

        config.datos_mercado[symbol].update({
            "precio_actual": precio,
            "variacion": variacion,
            "rsi": rsi,
            "ultima_actualizacion": hora_utc,
            "hora_venezuela": ahora_ve
        })

        # --- INVERSIÓN ---
        inv = config.inversiones.get(symbol, {})
        cantidad = inv.get("cantidad", 0)
        capital = inv.get("capital_invertido", 0)
        ganancia_deseada = inv.get("ganancia_deseada", 0)

        if cantidad > 0 and capital > 0 and ganancia_deseada > 0:
            valor_actual = cantidad * precio
            monto_total_deseado = capital + ganancia_deseada
            precio_objetivo = monto_total_deseado / cantidad
            ganancia_actual = ((valor_actual - capital) / capital) * 100

            config.datos_mercado[symbol].update({
                "capital_invertido": capital,
                "ganancia_deseada": ganancia_deseada,
                "monto_total_deseado": monto_total_deseado,
                "precio_objetivo": precio_objetivo,
                "valor_actual_inversion": valor_actual,
                "ganancia_actual": ganancia_actual
            })

            if valor_actual >= monto_total_deseado and not inv.get("alcanzado", False):
                nombre_completo = config.NOMBRES_MONEDAS.get(symbol, symbol)
                abreviatura = symbol.replace('USDT', '')
                tendencia = "📈 ALTA" if variacion >= 0 else "📉 BAJA"
                mensaje = (
                    f"🎯 *¡META ALCANZADA en {nombre_completo} ({abreviatura})!*\n"
                    f"💰 Capital invertido: ${capital:,.2f}\n"
                    f"🎯 Ganancia deseada: ${ganancia_deseada:,.2f}\n"
                    f"💵 Valor actual: ${valor_actual:,.2f}\n"
                    f"📈 Ganancia real: {ganancia_actual:+.2f}%\n"
                    f"📊 Precio actual: ${precio:,.2f}\n"
                    f"📉 Tendencia: {tendencia}\n"
                    f"🕒 Hora local: {ahora_ve}"
                )
                enviar_alerta_telegram(mensaje)
                config.inversiones[symbol]["alcanzado"] = True
                config.guardar_inversiones()

        # --- ALERTAS DE VARIACIÓN ---
        nombre_completo = config.NOMBRES_MONEDAS.get(symbol, symbol)
        abreviatura = symbol.replace('USDT', '')
        tendencia = "📈 ALTA" if variacion >= 0 else "📉 BAJA"

        if abs(variacion) >= config.VARIACION_ALERTA and not ultima_variacion_alerta[symbol]:
            signo = "+" if variacion > 0 else ""
            mensaje = (
                f"📊 *{nombre_completo} ({abreviatura}) - Variación significativa*\n"
                f"💰 Precio: ${precio:,.2f}\n"
                f"📈 Cambio 24h: {signo}{variacion:.2f}% ({tendencia})\n"
                f"🕒 Hora local: {ahora_ve}"
            )
            enviar_alerta_telegram(mensaje)
            ultima_variacion_alerta[symbol] = True
        elif abs(variacion) < config.VARIACION_ALERTA:
            ultima_variacion_alerta[symbol] = False

        # --- ALERTAS RSI ---
        estado_rsi = "Neutral"
        if rsi < config.RSI_SOBREVENTA:
            estado_rsi = "Sobrevendido"
        elif rsi > config.RSI_SOBRECOMPRA:
            estado_rsi = "Sobrecomprado"

        if estado_rsi != "Neutral" and ultimo_estado_rsi[symbol] != estado_rsi:
            emoji = "🔴" if estado_rsi == "Sobrevendido" else "🟢"
            mensaje = (
                f"{emoji} *{nombre_completo} ({abreviatura}) - Señal de RSI*\n"
                f"📊 RSI: {rsi:.2f} ({estado_rsi})\n"
                f"💰 Precio: ${precio:,.2f}\n"
                f"📈 Tendencia: {tendencia}\n"
                f"🕒 Hora local: {ahora_ve}"
            )
            enviar_alerta_telegram(mensaje)
            ultimo_estado_rsi[symbol] = estado_rsi
        elif estado_rsi == "Neutral":
            ultimo_estado_rsi[symbol] = None

    # --- RECOMENDACIONES ---
    for symbol in config.MONEDAS:
        ticker = tickers.get(symbol)
        if not ticker:
            continue
        precio = ticker["lastPrice"]
        variacion = ticker["priceChangePercent"]
        precios_hist = obtener_velas(symbol)
        if precios_hist is None:
            precios_hist = []
        
        rec = calcular_recomendacion(symbol, precio, precios_hist, variacion)
        config.recomendaciones[symbol] = rec

        # Notificación automática si cambia la recomendación o probabilidad alta
        ult = config.ultima_recomendacion_enviada.get(symbol, {})
        ult_rec = ult.get("recomendacion")
        ult_prob = ult.get("probabilidad", 0)
        recom = rec.get("recomendacion")
        prob = rec.get("probabilidad", 50)
        
        if recom in ["Comprar", "Vender"]:
            if (ult_rec != recom) or (prob >= 80 and ult_prob < 80):
                enviar_recomendacion_telegram(symbol, rec)
                config.ultima_recomendacion_enviada[symbol] = {
                    "recomendacion": recom,
                    "probabilidad": prob,
                    "timestamp": time.time()
                }
        else:
            if symbol in config.ultima_recomendacion_enviada:
                del config.ultima_recomendacion_enviada[symbol]

    # --- HISTORIAL ---
    moneda_sel = config.moneda_seleccionada
    if moneda_sel in config.datos_mercado:
        precio_sel = config.datos_mercado[moneda_sel]["precio_actual"]
        rsi_sel = config.datos_mercado[moneda_sel].get("rsi", 50.0)

        if (len(config.historial_analisis) == 0 or
            config.historial_analisis[0]["precio"] != precio_sel):
            estado_rsi_sel = "Neutral"
            if rsi_sel < 30:
                estado_rsi_sel = "Sobrevendido"
            elif rsi_sel > 70:
                estado_rsi_sel = "Sobrecomprado"
            config.historial_analisis.insert(0, {
                "fecha": ahora_ve,
                "precio": precio_sel,
                "estado": estado_rsi_sel
            })
            if len(config.historial_analisis) > HISTORIAL_MAX:
                config.historial_analisis.pop()

    config.actualizacion_event.set()
    config.logger.info(f"Datos actualizados para {len(config.MONEDAS)} monedas.")

def calcular_rsi_precios(precios):
    if not precios or len(precios) < 15:
        return 50.0
    cambios = [precios[i] - precios[i-1] for i in range(1, len(precios))]
    cambios_ultimos = cambios[-14:] if len(cambios) >= 14 else cambios
    ganancias = [c for c in cambios_ultimos if c > 0] or [0]
    perdidas = [abs(c) for c in cambios_ultimos if c < 0] or [0]
    n = len(cambios_ultimos)
    prom_ganancias = sum(ganancias) / n
    prom_perdidas = sum(perdidas) / n
    if prom_perdidas == 0:
        return 100.0
    rs = prom_ganancias / prom_perdidas
    return 100 - (100 / (1 + rs))

def enviar_alerta_manual():
    ahora_ve = datetime.now(config.ZONA_VE).strftime("%I:%M:%S %p")
    mensaje = f"📊 *Resumen CryptoAlert*\n🕒 Última actualización: {ahora_ve}\n\n"

    for symbol in config.MONEDAS:
        datos = config.datos_mercado.get(symbol, {})
        precio = datos.get("precio_actual", 0)
        variacion = datos.get("variacion", 0)
        rsi = datos.get("rsi", 50)
        nombre = config.NOMBRES_MONEDAS.get(symbol, symbol)
        abrev = symbol.replace('USDT', '')
        tendencia = "📈 ALTA" if variacion >= 0 else "📉 BAJA"
        mensaje += f"• *{nombre} ({abrev})*: ${precio:,.2f}  ({variacion:+.2f}%)  {tendencia}  RSI: {rsi:.2f}\n"

    inversiones_activas = False
    for symbol, inv in config.inversiones.items():
        if inv["cantidad"] > 0 and inv["capital_invertido"] > 0 and inv["ganancia_deseada"] > 0:
            inversiones_activas = True
            nombre = config.NOMBRES_MONEDAS.get(symbol, symbol)
            abrev = symbol.replace('USDT', '')
            precio_act = config.datos_mercado.get(symbol, {}).get("precio_actual", 0)
            valor = inv["cantidad"] * precio_act
            ganancia = ((valor - inv["capital_invertido"]) / inv["capital_invertido"]) * 100
            mensaje += f"\n💰 *{nombre} ({abrev}) - Inversión:*\n"
            mensaje += f"  Capital: ${inv['capital_invertido']:,.2f}\n"
            mensaje += f"  Ganancia deseada: ${inv['ganancia_deseada']:,.2f}\n"
            mensaje += f"  Valor actual: ${valor:,.2f}\n"
            mensaje += f"  Ganancia: {ganancia:+.2f}%"

    if not inversiones_activas:
        mensaje += "\n🔹 Sin inversiones configuradas."

    enviar_alerta_telegram(mensaje)
    config.logger.info("Alerta manual enviada.")

def bucle_bot():
    config.logger.info("🤖 Bot de análisis multi-moneda iniciado.")
    while True:
        try:
            analizar_mercado()
        except Exception as e:
            config.logger.error(f"Error en el bucle principal: {e}")
        time.sleep(INTERVALO_ACTUALIZACION)
