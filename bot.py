from datetime import datetime
import time
import requests
import config

# ============================================================
#  CONSTANTES
# ============================================================
HISTORIAL_MAX = 5
INTERVALO_ACTUALIZACION = 60   # segundos

# Variable global para la referencia de precio (cierre del día anterior)
precio_anterior = None

# Estados previos para evitar alertas repetitivas
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

def obtener_precio():
    """Obtiene velas diarias de BTC/USDT desde Binance o MEXC."""
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
                    return datos
                else:
                    config.logger.warning(f"{url} devolvió solo {len(datos)} velas.")
            else:
                config.logger.warning(f"{url} respondió con código {respuesta.status_code}")
        except Exception as e:
            config.logger.error(f"Error al consultar {url}: {e}")
            continue
    return None

def analizar_mercado():
    """Obtiene datos, calcula RSI y variación, actualiza estado y dispara alertas."""
    global precio_anterior, ultimo_estado_rsi, ultima_variacion_alerta

    datos = obtener_precio()
    if not datos:
        config.datos_mercado["ultima_actualizacion"] = "❌ Error API: Sin respuesta"
        config.logger.error("No se obtuvieron datos de las APIs.")
        return

    try:
        precios = [float(dia[4]) for dia in datos]
        precio_actual = precios[-1]

        # --- VARIACIÓN DIARIA ---
        if len(precios) >= 2:
            precio_ayer = precios[-2]
            if precio_anterior is None:
                precio_anterior = precio_ayer
            variacion = ((precio_actual - precio_anterior) / precio_anterior) * 100
            precio_anterior = precio_actual
        else:
            variacion = 0.0

        # --- RSI (14 periodos) ---
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

        # Hora actual en Venezuela (usando zoneinfo)
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
            ultimo_estado_rsi = None   # reset para futuros cruces

        # 2. Alerta por variación brusca (solo si supera umbral y no se ha enviado antes)
        if abs(variacion) >= config.VARIACION_ALERTA and not ultima_variacion_alerta:
            signo = "+" if variacion > 0 else ""
            mensaje = f"📈 BTC/USDT variación {signo}{variacion:.2f}% (vs. día anterior)\nPrecio: ${precio_actual:,.2f}"
            enviar_alerta_telegram(mensaje)
            ultima_variacion_alerta = True
        elif abs(variacion) < config.VARIACION_ALERTA:
            ultima_variacion_alerta = False   # rearmar

        # Disparar evento para SSE
        config.actualizacion_event.set()

        config.logger.info(f"Datos actualizados: precio=${precio_actual:,.2f}, RSI={rsi:.2f}, var={variacion:.2f}%")

    except Exception as e:
        config.logger.error(f"Error procesando datos: {e}")
        config.datos_mercado["ultima_actualizacion"] = f"❌ Error: {str(e)}"

def enviar_alerta_manual():
    """Envía un resumen de los datos actuales por Telegram (llamada desde la web)."""
    datos = config.datos_mercado
    mensaje = (
        f"📊 *Resumen CryptoAlert*\n"
        f"💰 Precio BTC: ${datos['precio_actual']:,.2f}\n"
        f"📈 RSI (14d): {datos['rsi']:.2f}\n"
        f"📉 Variación: {datos['variacion']:+.2f}%\n"
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
