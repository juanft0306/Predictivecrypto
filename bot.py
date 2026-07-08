from datetime import datetime, timedelta
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

# ============================================================
#  FUNCIONES AUXILIARES
# ============================================================
def enviar_alerta_telegram(mensaje):
    """Envía un mensaje al chat de Telegram si las credenciales están configuradas."""
    if not config.TOKEN_TELEGRAM or not config.CHAT_ID_TELEGRAM:
        print("⚠️  Token o Chat ID no configurados. No se enviará alerta.")
        return
    url = f"https://api.telegram.org/bot{config.TOKEN_TELEGRAM}/sendMessage"
    payload = {"chat_id": config.CHAT_ID_TELEGRAM, "text": mensaje}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"❌ Error al enviar mensaje a Telegram: {e}")

def obtener_precio():
    """
    Obtiene los datos de velas diarias de BTC/USDT desde Binance o MEXC.
    Retorna la lista de velas (JSON) o None si falla.
    Necesita al menos 2 velas para calcular la variación diaria.
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
                if len(datos) >= 2:  # Necesitamos al menos dos precios (ayer y hoy)
                    return datos
                else:
                    print(f"⚠️  {url} devolvió solo {len(datos)} velas, se necesitan al menos 2.")
            else:
                print(f"⚠️  {url} respondió con código {respuesta.status_code}")
        except Exception as e:
            print(f"❌ Error al consultar {url}: {e}")
            continue
    return None

def analizar_mercado():
    """Obtiene datos, calcula RSI y variación diaria, actualiza el estado global."""
    global precio_anterior

    datos = obtener_precio()
    if not datos:
        config.datos_mercado["ultima_actualizacion"] = "❌ Error API: Sin respuesta"
        # No se dispara el evento porque no hay datos válidos
        return

    try:
        precios = [float(dia[4]) for dia in datos]   # Precios de cierre
        precio_actual = precios[-1]

        # --- VARIACIÓN DIARIA (respecto al cierre del día anterior) ---
        if len(precios) >= 2:
            precio_ayer = precios[-2]
            if precio_anterior is None:
                precio_anterior = precio_ayer  # primera ejecución
            variacion = ((precio_actual - precio_anterior) / precio_anterior) * 100
            # Actualizar referencia para la próxima iteración
            precio_anterior = precio_actual   # ahora el "ayer" será el actual
        else:
            variacion = 0.0

        # --- CÁLCULO DEL RSI (14 periodos) ---
        if len(precios) < 15:
            rsi = 50.0   # valor neutro si no hay suficientes datos
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

        # Hora actual en Venezuela (UTC-4)
        ahora_ve = (datetime.utcnow() - timedelta(hours=4)).strftime("%I:%M:%S %p")

        # Actualizar el diccionario central
        config.datos_mercado.update({
            "precio_actual": precio_actual,
            "rsi": rsi,
            "variacion": variacion,
            "ultima_actualizacion": datetime.utcnow().strftime("%H:%M:%S UTC"),
            "hora_venezuela": ahora_ve
        })

        # --- ACTUALIZAR HISTORIAL (solo si cambió el precio) ---
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

        # --- DISPARAR EVENTO PARA SSE ---
        config.actualizacion_event.set()

    except Exception as e:
        print(f"❌ Error procesando datos: {e}")
        config.datos_mercado["ultima_actualizacion"] = f"❌ Error: {str(e)}"

def bucle_bot():
    """Bucle principal que ejecuta el análisis cada INTERVALO_ACTUALIZACION segundos."""
    print("🤖 Bot de análisis de mercado iniciado.")
    if not config.TOKEN_TELEGRAM or not config.CHAT_ID_TELEGRAM:
        print("⚠️  Credenciales de Telegram no configuradas. Las alertas no funcionarán.")
    else:
        print("✅ Credenciales de Telegram cargadas.")
    while True:
        try:
            analizar_mercado()
        except Exception as e:
            print(f"❌ Error en el bucle principal: {e}")
        time.sleep(INTERVALO_ACTUALIZACION)
