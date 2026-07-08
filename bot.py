from datetime import datetime
import time
import requests
import config

# ============================================================
#  CONSTANTES
# ============================================================
HISTORIAL_MAX = 5
INTERVALO_ACTUALIZACION = 10

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
    if not config.TOKEN_TELEGRAM or not config.CHAT_ID_TELEGRAM:
        config.logger.warning("Credenciales de Telegram no configuradas.")
        return
    url = f"https://api.telegram.org/bot{config.TOKEN_TELEGRAM}/sendMessage"
    payload = {"chat_id": config.CHAT_ID_TELEGRAM, "text": mensaje}
    try:
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code != 200:
            config.logger.error(f"Error al enviar alerta: {resp.text}")
    except Exception as e:
        config.logger.error(f"Excepción al enviar alerta: {e}")

def obtener_todos_los_tickers():
    """
    Obtiene los tickers de 24h de Binance y filtra solo los pares que nos interesan.
    Retorna un dict { "BTCUSDT": { "lastPrice": 62000, "priceChangePercent": -2.64 }, ... }
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
            config.logger.warning(f"Ticker 24h respondió {resp.status_code}")
    except Exception as e:
        config.logger.error(f"Error en ticker 24h: {e}")
    return None

def obtener_velas(symbol):
    """Obtiene velas diarias para una moneda específica (para calcular RSI)."""
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
                    return [float(dia[4]) for dia in datos]
                else:
                    config.logger.warning(f"{url} devolvió solo {len(datos)} velas.")
            else:
                config.logger.warning(f"{url} respondió {resp.status_code}")
        except Exception as e:
            config.logger.error(f"Error en {url}: {e}")
    return None

def calcular_rsi(precios):
    """Calcula RSI (14 periodos) a partir de una lista de precios de cierre."""
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
    """Obtiene datos de todas las monedas, calcula RSI para cada una y actualiza estados."""
    global ultimo_estado_rsi, ultima_variacion_alerta

    tickers = obtener_todos_los_tickers()
    if not tickers:
        config.logger.error("No se obtuvieron tickers de Binance.")
        return

    ahora_ve = datetime.now(config.ZONA_VE).strftime("%I:%M:%S %p")
    hora_utc = datetime.utcnow().strftime("%H:%M:%S UTC")

    # Procesar cada moneda
    for symbol in config.MONEDAS:
        if symbol not in tickers:
            config.logger.warning(f"No hay datos para {symbol}, se salta.")
            continue

        ticker = tickers[symbol]
        precio = ticker["lastPrice"]
        variacion = ticker["priceChangePercent"]

        # Obtener velas para RSI (usamos caché simple, pero aquí lo hacemos siempre)
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

        # Alertas automáticas por moneda

        # 1. Alerta de variación brusca
        if abs(variacion) >= config.VARIACION_ALERTA and not ultima_variacion_alerta[symbol]:
            signo = "+" if variacion > 0 else ""
            mensaje = f"📈 {symbol} variación {signo}{variacion:.2f}% (24h)\nPrecio: ${precio:,.2f}"
            enviar_alerta_telegram(mensaje)
            ultima_variacion_alerta[symbol] = True
        elif abs(variacion) < config.VARIACION_ALERTA:
            ultima_variacion_alerta[symbol] = False

        # 2. Alerta de RSI (sobrecompra/sobreventa)
        estado_rsi = "Neutral"
        if rsi < config.RSI_SOBREVENTA:
            estado_rsi = "Sobrevendido"
        elif rsi > config.RSI_SOBRECOMPRA:
            estado_rsi = "Sobrecomprado"

        if estado_rsi != "Neutral" and ultimo_estado_rsi[symbol] != estado_rsi:
            emoji = "🔴" if estado_rsi == "Sobrevendido" else "🟢"
            mensaje = f"{emoji} {symbol} en {estado_rsi} (RSI={rsi:.2f})\nPrecio: ${precio:,.2f}"
            enviar_alerta_telegram(mensaje)
            ultimo_estado_rsi[symbol] = estado_rsi
        elif estado_rsi == "Neutral":
            ultimo_estado_rsi[symbol] = None

        # 3. Alerta de objetivo de inversión (solo para esta moneda si tiene inversión activa)
        inv = config.inversiones.get(symbol, {})
        if inv.get("cantidad", 0) > 0 and inv.get("objetivo", 0) > 0:
            if precio >= inv["objetivo"] and not inv.get("alcanzado", False):
                cantidad = inv["cantidad"]
                valor_actual = cantidad * precio
                ganancia = ((precio - inv["objetivo"]) / inv["objetivo"]) * 100
                mensaje = (
                    f"🎯 *¡OBJETIVO ALCANZADO en {symbol}!*\n"
                    f"Precio actual: ${precio:,.2f}\n"
                    f"Tu inversión: {cantidad:.8f} {symbol.replace('USDT', '')}\n"
                    f"Valor actual: ${valor_actual:,.2f}\n"
                    f"Objetivo: ${inv['objetivo']:,.2f}\n"
                    f"Ganancia: {ganancia:+.2f}%"
                )
                enviar_alerta_telegram(mensaje)
                config.inversiones[symbol]["alcanzado"] = True

    # Actualizar historial solo para la moneda seleccionada en inversión
    moneda_sel = config.moneda_seleccionada
    if moneda_sel in config.datos_mercado:
        precio_sel = config.datos_mercado[moneda_sel]["precio_actual"]
        rsi_sel = config.datos_mercado[moneda_sel].get("rsi", 50.0)

        if (len(config.historial_analisis) == 0 or
            config.historial_analisis[0]["precio"] != precio_sel):
            estado_rsi_sel = "Neutral"
            if rsi_sel < 30: estado_rsi_sel = "Sobrevendido"
            elif rsi_sel > 70: estado_rsi_sel = "Sobrecomprado"
            config.historial_analisis.insert(0, {
                "fecha": ahora_ve,
                "precio": precio_sel,
                "estado": estado_rsi_sel
            })
            if len(config.historial_analisis) > HISTORIAL_MAX:
                config.historial_analisis.pop()

    # Disparar evento SSE
    config.actualizacion_event.set()

    config.logger.info(f"Datos actualizados para {len(config.MONEDAS)} monedas.")

def enviar_alerta_manual():
    """Envía un resumen de todos los datos por Telegram."""
    mensaje = "📊 *Resumen CryptoAlert*\n"
    for symbol in config.MONEDAS:
        datos = config.datos_mercado.get(symbol, {})
        precio = datos.get("precio_actual", 0)
        variacion = datos.get("variacion", 0)
        mensaje += f"\n• {symbol}: ${precio:,.2f} ({variacion:+.2f}%)"

    # Añadir datos de inversiones activas
    inversiones_activas = False
    for symbol, inv in config.inversiones.items():
        if inv["cantidad"] > 0 and inv["objetivo"] > 0:
            inversiones_activas = True
            precio_act = config.datos_mercado.get(symbol, {}).get("precio_actual", 0)
            valor = inv["cantidad"] * precio_act
            ganancia = ((precio_act - inv["objetivo"]) / inv["objetivo"]) * 100
            mensaje += f"\n\n💰 *{symbol} Inversión:*\n"
            mensaje += f"Cantidad: {inv['cantidad']:.8f}\n"
            mensaje += f"Valor: ${valor:,.2f}\n"
            mensaje += f"Objetivo: ${inv['objetivo']:,.2f}\n"
            mensaje += f"Ganancia: {ganancia:+.2f}%"

    if not inversiones_activas:
        mensaje += "\n\n🔹 Sin inversiones configuradas."

    enviar_alerta_telegram(mensaje)
    config.logger.info("Alerta manual enviada.")

def bucle_bot():
    config.logger.info("🤖 Bot de análisis multi-moneda iniciado.")
    while True:
        try:
            analizar_mercado()
        except Exception as e:
            config.logger.error(f"Error en bucle: {e}")
        time.sleep(INTERVALO_ACTUALIZACION)
