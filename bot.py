from datetime import datetime
import time
import requests
import config

# ============================================================
#  CONSTANTES
# ============================================================
HISTORIAL_MAX = 5
INTERVALO_ACTUALIZACION = 10   # segundos

# Estados previos para alertas (por moneda)
ultimo_estado_rsi = {}
ultima_variacion_alerta = {}

for moneda in config.MONEDAS:
    ultimo_estado_rsi[moneda] = None
    ultima_variacion_alerta[moneda] = False

# ============================================================
#  FUNCIONES AUXILIARES
# ============================================================
def enviar_alerta_telegram(mensaje):
    """
    Envía un mensaje a Telegram con formato Markdown.
    Si no hay credenciales, solo registra un warning.
    """
    if not config.TOKEN_TELEGRAM or not config.CHAT_ID_TELEGRAM:
        config.logger.warning("Credenciales de Telegram no configuradas. Alerta no enviada.")
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

def obtener_todos_los_tickers():
    """
    Obtiene los tickers de 24h de Binance y filtra solo los pares que nos interesan.
    Retorna un dict: { "BTCUSDT": { "lastPrice": 62000, "priceChangePercent": -2.64 }, ... }
    """
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
    """
    Obtiene velas diarias para una moneda específica (para calcular RSI).
    Retorna lista de precios de cierre o None.
    """
    endpoints = [
        f"https://api.binance.us/api/v3/klines?symbol={symbol}&interval=1d&limit=15",
        f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval=1d&limit=15"
    ]
    for url in endpoints:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                datos = resp.json()
                if len(datos) >= 2:
                    return [float(dia[4]) for dia in datos]  # precio de cierre
                else:
                    config.logger.warning(f"{url} devolvió solo {len(datos)} velas.")
            else:
                config.logger.warning(f"{url} respondió con código {resp.status_code}")
        except Exception as e:
            config.logger.error(f"Error en {url}: {e}")
    return None

def calcular_rsi(precios):
    """
    Calcula RSI (14 periodos) a partir de una lista de precios de cierre.
    Retorna valor RSI o 50.0 si no hay suficientes datos.
    """
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

def analizar_mercado():
    """
    Obtiene datos de todas las monedas, calcula RSI para cada una,
    actualiza estados y dispara alertas automáticas.
    """
    global ultimo_estado_rsi, ultima_variacion_alerta

    # 1. Obtener todos los tickers de 24h
    tickers = obtener_todos_los_tickers()
    if not tickers:
        config.logger.error("No se obtuvieron tickers de Binance.")
        return

    ahora_ve = datetime.now(config.ZONA_VE).strftime("%I:%M:%S %p")
    hora_utc = datetime.utcnow().strftime("%H:%M:%S UTC")

    # 2. Procesar cada moneda
    for symbol in config.MONEDAS:
        if symbol not in tickers:
            config.logger.warning(f"No hay datos para {symbol}, se salta.")
            continue

        ticker = tickers[symbol]
        precio = ticker["lastPrice"]
        variacion = ticker["priceChangePercent"]

        # Obtener velas para RSI
        precios = obtener_velas(symbol)
        rsi = calcular_rsi(precios) if precios else 50.0

        # Actualizar datos de mercado
        config.datos_mercado[symbol].update({
            "precio_actual": precio,
            "variacion": variacion,
            "rsi": rsi,
            "ultima_actualizacion": hora_utc,
            "hora_venezuela": ahora_ve
        })

        # --- ALERTAS AUTOMÁTICAS POR MONEDA ---

        # 2.1 Alerta de variación brusca (umbral VARIACION_ALERTA)
        if abs(variacion) >= config.VARIACION_ALERTA and not ultima_variacion_alerta[symbol]:
            signo = "+" if variacion > 0 else ""
            mensaje = (
                f"📊 *{symbol} - Variación significativa*\n"
                f"💰 Precio: ${precio:,.2f}\n"
                f"📈 Cambio 24h: {signo}{variacion:.2f}%\n"
                f"🕒 Hora: {ahora_ve}"
            )
            enviar_alerta_telegram(mensaje)
            ultima_variacion_alerta[symbol] = True
        elif abs(variacion) < config.VARIACION_ALERTA:
            ultima_variacion_alerta[symbol] = False

        # 2.2 Alerta de RSI (sobrecompra/sobreventa)
        estado_rsi = "Neutral"
        if rsi < config.RSI_SOBREVENTA:
            estado_rsi = "Sobrevendido"
        elif rsi > config.RSI_SOBRECOMPRA:
            estado_rsi = "Sobrecomprado"

        if estado_rsi != "Neutral" and ultimo_estado_rsi[symbol] != estado_rsi:
            emoji = "🔴" if estado_rsi == "Sobrevendido" else "🟢"
            mensaje = (
                f"{emoji} *{symbol} - Señal de RSI*\n"
                f"📊 RSI: {rsi:.2f} ({estado_rsi})\n"
                f"💰 Precio: ${precio:,.2f}\n"
                f"🕒 Hora: {ahora_ve}"
            )
            enviar_alerta_telegram(mensaje)
            ultimo_estado_rsi[symbol] = estado_rsi
        elif estado_rsi == "Neutral":
            ultimo_estado_rsi[symbol] = None

        # 2.3 Alerta de objetivo de inversión (si está configurado)
        inv = config.inversiones.get(symbol, {})
        if inv.get("cantidad", 0) > 0 and inv.get("objetivo", 0) > 0:
            if precio >= inv["objetivo"] and not inv.get("alcanzado", False):
                cantidad = inv["cantidad"]
                valor_actual = cantidad * precio
                ganancia = ((precio - inv["objetivo"]) / inv["objetivo"]) * 100
                mensaje = (
                    f"🎯 *¡OBJETIVO ALCANZADO en {symbol}!*\n"
                    f"💰 Precio actual: ${precio:,.2f}\n"
                    f"📊 Tu inversión: {cantidad:.8f} {symbol.replace('USDT', '')}\n"
                    f"💵 Valor actual: ${valor_actual:,.2f}\n"
                    f"🎯 Objetivo: ${inv['objetivo']:,.2f}\n"
                    f"📈 Ganancia: {ganancia:+.2f}%\n"
                    f"🕒 Hora: {ahora_ve}"
                )
                enviar_alerta_telegram(mensaje)
                config.inversiones[symbol]["alcanzado"] = True

    # 3. Actualizar historial solo para la moneda seleccionada en inversión
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

    # 4. Disparar evento SSE para notificar cambios
    config.actualizacion_event.set()

    config.logger.info(f"Datos actualizados para {len(config.MONEDAS)} monedas.")

def enviar_alerta_manual():
    """
    Envía un resumen completo de todas las monedas y las inversiones activas
    por Telegram (llamada desde el botón "Enviar alerta").
    """
    mensaje = "📊 *Resumen CryptoAlert*\n\n"
    for symbol in config.MONEDAS:
        datos = config.datos_mercado.get(symbol, {})
        precio = datos.get("precio_actual", 0)
        variacion = datos.get("variacion", 0)
        rsi = datos.get("rsi", 50)
        mensaje += f"• *{symbol}*: ${precio:,.2f}  ({variacion:+.2f}%)  RSI: {rsi:.2f}\n"

    # Añadir inversiones activas
    inversiones_activas = False
    for symbol, inv in config.inversiones.items():
        if inv["cantidad"] > 0 and inv["objetivo"] > 0:
            inversiones_activas = True
            precio_act = config.datos_mercado.get(symbol, {}).get("precio_actual", 0)
            valor = inv["cantidad"] * precio_act
            ganancia = ((precio_act - inv["objetivo"]) / inv["objetivo"]) * 100
            mensaje += f"\n💰 *{symbol} Inversión:*\n"
            mensaje += f"  Cantidad: {inv['cantidad']:.8f}\n"
            mensaje += f"  Valor: ${valor:,.2f}\n"
            mensaje += f"  Objetivo: ${inv['objetivo']:,.2f}\n"
            mensaje += f"  Ganancia: {ganancia:+.2f}%"

    if not inversiones_activas:
        mensaje += "\n🔹 Sin inversiones configuradas."

    ahora = datetime.now(config.ZONA_VE).strftime("%I:%M:%S %p")
    mensaje += f"\n\n🕒 Última actualización: {ahora}"

    enviar_alerta_telegram(mensaje)
    config.logger.info("Alerta manual enviada.")

def bucle_bot():
    """
    Bucle principal que ejecuta el análisis cada INTERVALO_ACTUALIZACION segundos.
    """
    config.logger.info("🤖 Bot de análisis multi-moneda iniciado.")
    while True:
        try:
            analizar_mercado()
        except Exception as e:
            config.logger.error(f"Error en el bucle principal: {e}")
        time.sleep(INTERVALO_ACTUALIZACION)
