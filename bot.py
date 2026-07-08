from datetime import datetime
import time
import requests
import config

# ============================================================
#  CONSTANTES
# ============================================================
HISTORIAL_MAX = 5
INTERVALO_ACTUALIZACION = 10   # 10 segundos

# Variable global para la referencia de precio (ya no la usamos para variación)
# pero la mantenemos por si falla la API de ticker.
precio_anterior = None

# Estados previos para alertas
ultimo_estado_rsi = None
ultima_variacion_alerta = False

# ============================================================
#  FUNCIONES AUXILIARES
# ============================================================
def enviar_alerta_telegram(mensaje):
    """Envía un mensaje al chat de Telegram."""
    if not config.TOKEN_TELEGRAM or not config.CHAT_ID_TELEGRAM:
        config.logger.warning("Credenciales de Telegram no configuradas. Alerta no enviada.")
        return
    url = f"https://api.telegram.org/bot{config.TOKEN_TELEGRAM}/sendMessage"
    payload = {"chat_id": config.CHAT_ID_TELEGRAM, "text": mensaje}
    try:
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code != 200:
            config.logger.error(f"Error al enviar alerta: {resp.text}")
    except Exception as e:
        config.logger.error(f"Excepción al enviar alerta: {e}")

def obtener_variacion_binance():
    """
    Obtiene el precio actual y la variación porcentual en 24h desde Binance.
    Retorna (precio_actual, variacion) o (None, None) si falla.
    """
    url = "https://api.binance.us/api/v3/ticker/24hr?symbol=BTCUSDT"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            precio_actual = float(data['lastPrice'])
            variacion = float(data['priceChangePercent'])
            return precio_actual, variacion
        else:
            config.logger.warning(f"Ticker 24h respondió con código {resp.status_code}")
    except Exception as e:
        config.logger.error(f"Error al consultar ticker 24h: {e}")
    return None, None

def obtener_velas():
    """
    Obtiene las velas diarias de BTC/USDT desde Binance o MEXC para el RSI.
    Retorna lista de precios de cierre o None.
    """
    endpoints = [
        "https://api.binance.us/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=15",
        "https://api.mexc.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=15"
    ]
    for url in endpoints:
        try:
            respuesta = requests.get(url, timeout=5)
            if respuesta.status_code == 200:
                datos = respuesta.json()
                if len(datos) >= 2:
                    return [float(dia[4]) for dia in datos]  # precios de cierre
                else:
                    config.logger.warning(f"{url} devolvió solo {len(datos)} velas.")
            else:
                config.logger.warning(f"{url} respondió con código {respuesta.status_code}")
        except Exception as e:
            config.logger.error(f"Error al consultar {url}: {e}")
            continue
    return None

def analizar_mercado():
    """Obtiene datos, calcula RSI, usa variación de Binance y actualiza estado."""
    global ultimo_estado_rsi, ultima_variacion_alerta

    # 1. Obtener precio y variación desde el ticker de 24h
    precio_actual, variacion = obtener_variacion_binance()
    if precio_actual is None or variacion is None:
        # Si falla, intentamos con el método antiguo (velas) como respaldo
        config.logger.warning("Fallo ticker 24h, usando respaldo con velas.")
        precios = obtener_velas()
        if not precios:
            config.datos_mercado["ultima_actualizacion"] = "❌ Error API: Sin respuesta"
            config.logger.error("No se obtuvieron datos de las APIs.")
            return
        precio_actual = precios[-1]
        if len(precios) >= 2:
            precio_ayer = precios[-2]
            variacion = ((precio_actual - precio_ayer) / precio_ayer) * 100
        else:
            variacion = 0.0
    else:
        # Si obtuvimos bien el ticker, también necesitamos las velas para el RSI
        precios = obtener_velas()
        if not precios:
            # Si no hay velas, no podemos calcular RSI, pero al menos tenemos precio y variación
            config.logger.warning("No se obtuvieron velas para RSI, se usará RSI=50")
            rsi = 50.0
        else:
            # Calcular RSI con las velas obtenidas
            if len(precios) < 15:
                rsi = 50.0
            else:
                cambios = [precios[i] - precios[i-1] for i in range(1, len(precios))]
                cambios_ultimos = cambios[-14:] if len(cambios) >= 14 else cambios
                ganancias = [c for c in cambios_ultimos if c > 0] or [0]
                perdidas = [abs(c) for c in cambios_ultimos if c < 0] or [0]
                n = len(cambios_ultimos)
                promedio_ganancias = sum(ganancias) / n
                promedio_perdidas = sum(perdidas) / n
                if promedio_perdidas == 0:
                    rsi = 100.0
                else:
                    rs = promedio_ganancias / promedio_perdidas
                    rsi = 100 - (100 / (1 + rs))
    # Nota: si ya teníamos precio y variación del ticker, y también obtuvimos precios para RSI,
    # el bloque anterior ya calculó rsi. Si no, rsi ya fue asignado.

    # Hora actual en Venezuela
    ahora_ve = datetime.now(config.ZONA_VE).strftime("%I:%M:%S %p")

    # Actualizar diccionario central
    config.datos_mercado.update({
        "precio_actual": precio_actual,
        "rsi": rsi,
        "variacion": variacion,
        "ultima_actualizacion": datetime.utcnow().strftime("%H:%M:%S UTC"),
        "hora_venezuela": ahora_ve
    })

    # --- ACTUALIZAR HISTORIAL ---
    if (len(config.historial_analisis) == 0 or
        config.historial_analisis[0]["precio"] != precio_actual):
        estado_rsi = "Neutral"
        if rsi < 30:
            estado_rsi = "Sobrevendido"
        elif rsi > 70:
            estado_rsi = "Sobrecomprado"
        config.historial_analisis.insert(0, {
            "fecha": ahora_ve,
            "precio": precio_actual,
            "estado": estado_rsi
        })
        if len(config.historial_analisis) > HISTORIAL_MAX:
            config.historial_analisis.pop()

    # --- ALERTAS AUTOMÁTICAS ---
    # 1. Alerta por RSI (solo si cambia de estado)
    if rsi < config.RSI_SOBREVENTA and ultimo_estado_rsi != "sobrevendido":
        mensaje = f"🔴 BTC/USDT en SOBREVENTA (RSI={rsi:.2f})\nPrecio: ${precio_actual:,.2f}"
        enviar_alerta_telegram(mensaje)
        ultimo_estado_rsi = "sobrevendido"
    elif rsi > config.RSI_SOBRECOMPRA and ultimo_estado_rsi != "sobrecomprado":
        mensaje = f"🟢 BTC/USDT en SOBRECOMPRA (RSI={rsi:.2f})\nPrecio: ${precio_actual:,.2f}"
        enviar_alerta_telegram(mensaje)
        ultimo_estado_rsi = "sobrecomprado"
    elif (rsi >= config.RSI_SOBREVENTA and rsi <= config.RSI_SOBRECOMPRA and
          ultimo_estado_rsi is not None):
        ultimo_estado_rsi = None

    # 2. Alerta por variación brusca (usando la variación de Binance)
    if abs(variacion) >= config.VARIACION_ALERTA and not ultima_variacion_alerta:
        signo = "+" if variacion > 0 else ""
        mensaje = f"📈 BTC/USDT variación {signo}{variacion:.2f}% (24h)\nPrecio: ${precio_actual:,.2f}"
        enviar_alerta_telegram(mensaje)
        ultima_variacion_alerta = True
    elif abs(variacion) < config.VARIACION_ALERTA:
        ultima_variacion_alerta = False

    # Disparar evento SSE
    config.actualizacion_event.set()

    config.logger.info(f"Datos actualizados: precio=${precio_actual:,.2f}, RSI={rsi:.2f}, var={variacion:.2f}%")

def enviar_alerta_manual():
    """Envía un resumen de los datos actuales por Telegram."""
    datos = config.datos_mercado
    mensaje = (
        f"📊 *Resumen CryptoAlert*\n"
        f"💰 Precio BTC: ${datos['precio_actual']:,.2f}\n"
        f"📈 RSI (14d): {datos['rsi']:.2f}\n"
        f"📉 Variación 24h: {datos['variacion']:+.2f}%\n"
        f"🕒 Hora: {datos['hora_venezuela']}\n"
        f"📅 Actualización: {datos['ultima_actualizacion']}"
    )
    enviar_alerta_telegram(mensaje)
    config.logger.info("Alerta manual enviada.")

def bucle_bot():
    """Bucle principal."""
    config.logger.info("🤖 Bot de análisis de mercado iniciado.")
    while True:
        try:
            analizar_mercado()
        except Exception as e:
            config.logger.error(f"Error en el bucle principal: {e}")
        time.sleep(INTERVALO_ACTUALIZACION)
