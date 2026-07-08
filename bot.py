from datetime import datetime
import time
import requests
import config

# ============================================================
#  CONSTANTES
# ============================================================
HISTORIAL_MAX = 5
INTERVALO_ACTUALIZACION = 10

# Estados previos para alertas
ultimo_estado_rsi = None
ultima_variacion_alerta = False

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

def obtener_variacion_binance():
    url = "https://api.binance.us/api/v3/ticker/24hr?symbol=BTCUSDT"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            precio_actual = float(data['lastPrice'])
            variacion = float(data['priceChangePercent'])
            return precio_actual, variacion
        else:
            config.logger.warning(f"Ticker 24h respondió {resp.status_code}")
    except Exception as e:
        config.logger.error(f"Error en ticker 24h: {e}")
    return None, None

def obtener_velas():
    endpoints = [
        "https://api.binance.us/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=15",
        "https://api.mexc.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=15"
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

def analizar_mercado():
    global ultimo_estado_rsi, ultima_variacion_alerta

    # 1. Obtener precio y variación desde ticker 24h
    precio_actual, variacion = obtener_variacion_binance()
    if precio_actual is None or variacion is None:
        # Fallback a velas
        config.logger.warning("Fallo ticker 24h, usando respaldo con velas.")
        precios = obtener_velas()
        if not precios:
            config.datos_mercado["ultima_actualizacion"] = "❌ Error API"
            config.logger.error("No se obtuvieron datos.")
            return
        precio_actual = precios[-1]
        if len(precios) >= 2:
            variacion = ((precio_actual - precios[-2]) / precios[-2]) * 100
        else:
            variacion = 0.0
        # Usar precios para RSI
        precios_rsi = precios
    else:
        # Si ticker funciona, obtener velas solo para RSI
        precios_rsi = obtener_velas()

    # 2. Calcular RSI
    if precios_rsi and len(precios_rsi) >= 15:
        cambios = [precios_rsi[i] - precios_rsi[i-1] for i in range(1, len(precios_rsi))]
        cambios_ultimos = cambios[-14:] if len(cambios) >= 14 else cambios
        ganancias = [c for c in cambios_ultimos if c > 0] or [0]
        perdidas = [abs(c) for c in cambios_ultimos if c < 0] or [0]
        n = len(cambios_ultimos)
        prom_ganancias = sum(ganancias) / n
        prom_perdidas = sum(perdidas) / n
        if prom_perdidas == 0:
            rsi = 100.0
        else:
            rs = prom_ganancias / prom_perdidas
            rsi = 100 - (100 / (1 + rs))
    else:
        rsi = 50.0   # valor por defecto

    # 3. Hora Venezuela
    ahora_ve = datetime.now(config.ZONA_VE).strftime("%I:%M:%S %p")

    # 4. Actualizar datos de mercado
    config.datos_mercado.update({
        "precio_actual": precio_actual,
        "rsi": rsi,
        "variacion": variacion,
        "ultima_actualizacion": datetime.utcnow().strftime("%H:%M:%S UTC"),
        "hora_venezuela": ahora_ve
    })

    # 5. SEGUIMIENTO DE INVERSIÓN
    if config.cantidad_btc > 0 and config.precio_objetivo > 0:
        valor_actual = config.cantidad_btc * precio_actual
        ganancia_perdida = ((precio_actual - config.precio_objetivo) / config.precio_objetivo) * 100
        config.datos_mercado.update({
            "cantidad_btc": config.cantidad_btc,
            "precio_objetivo": config.precio_objetivo,
            "valor_inversion": valor_actual,
            "ganancia_perdida": ganancia_perdida
        })
        # Comprobar si se alcanzó el objetivo (y no notificado aún)
        if precio_actual >= config.precio_objetivo and not config.objetivo_alcanzado:
            mensaje = (
                f"🎯 *¡OBJETIVO ALCANZADO!*\n"
                f"BTC ha alcanzado ${precio_actual:,.2f}\n"
                f"Tu inversión: {config.cantidad_btc:.8f} BTC\n"
                f"Valor actual: ${valor_actual:,.2f}\n"
                f"Objetivo: ${config.precio_objetivo:,.2f}\n"
                f"Ganancia: {ganancia_perdida:+.2f}%"
            )
            enviar_alerta_telegram(mensaje)
            config.objetivo_alcanzado = True
    else:
        # Limpiar datos de inversión si no hay configuración
        config.datos_mercado.update({
            "cantidad_btc": 0.0,
            "precio_objetivo": 0.0,
            "valor_inversion": 0.0,
            "ganancia_perdida": 0.0
        })

    # 6. Historial (solo si cambia el precio)
    if (len(config.historial_analisis) == 0 or
        config.historial_analisis[0]["precio"] != precio_actual):
        estado_rsi = "Neutral"
        if rsi < 30: estado_rsi = "Sobrevendido"
        elif rsi > 70: estado_rsi = "Sobrecomprado"
        config.historial_analisis.insert(0, {
            "fecha": ahora_ve,
            "precio": precio_actual,
            "estado": estado_rsi
        })
        if len(config.historial_analisis) > HISTORIAL_MAX:
            config.historial_analisis.pop()

    # 7. Alertas automáticas (RSI y variación)
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

    if abs(variacion) >= config.VARIACION_ALERTA and not ultima_variacion_alerta:
        signo = "+" if variacion > 0 else ""
        mensaje = f"📈 BTC/USDT variación {signo}{variacion:.2f}% (24h)\nPrecio: ${precio_actual:,.2f}"
        enviar_alerta_telegram(mensaje)
        ultima_variacion_alerta = True
    elif abs(variacion) < config.VARIACION_ALERTA:
        ultima_variacion_alerta = False

    # 8. Disparar evento SSE
    config.actualizacion_event.set()

    config.logger.info(f"Datos actualizados: precio=${precio_actual:,.2f}, RSI={rsi:.2f}, var={variacion:.2f}%")

def enviar_alerta_manual():
    datos = config.datos_mercado
    mensaje = (
        f"📊 *Resumen CryptoAlert*\n"
        f"💰 Precio BTC: ${datos['precio_actual']:,.2f}\n"
        f"📈 RSI (14d): {datos['rsi']:.2f}\n"
        f"📉 Variación 24h: {datos['variacion']:+.2f}%\n"
        f"🕒 Hora: {datos['hora_venezuela']}\n"
        f"📅 Actualización: {datos['ultima_actualizacion']}"
    )
    if config.cantidad_btc > 0:
        mensaje += (
            f"\n\n💰 *Inversión:*\n"
            f"BTC: {config.cantidad_btc:.8f}\n"
            f"Valor: ${datos['valor_inversion']:,.2f}\n"
            f"Objetivo: ${config.precio_objetivo:,.2f}\n"
            f"Ganancia: {datos['ganancia_perdida']:+.2f}%"
        )
    enviar_alerta_telegram(mensaje)
    config.logger.info("Alerta manual enviada.")

def bucle_bot():
    config.logger.info("🤖 Bot de análisis de mercado iniciado.")
    while True:
        try:
            analizar_mercado()
        except Exception as e:
            config.logger.error(f"Error en bucle: {e}")
        time.sleep(INTERVALO_ACTUALIZACION)
