from datetime import datetime, timedelta
import time
import requests
import config

# Variable global para calcular la ganancia/pérdida
precio_referencia = None

def enviar_alerta_telegram(mensaje):
    url = f"https://api.telegram.org/bot{config.TOKEN_TELEGRAM}/sendMessage"
    payload = {"chat_id": config.CHAT_ID_TELEGRAM, "text": mensaje}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print("❌ Error al enviar a Telegram:", e, flush=True)

def analizar_mercado():
    global precio_referencia
    
    endpoints = [
        "https://api.binance.us/api/v3/klines",
        "https://api.mexc.com/api/v3/klines"
    ]
    
    respuesta = None
    ultimo_error = ""
    
    # Intento de conexión
    for url in endpoints:
        try:
            url_completa = f"{url}?symbol=BTCUSDT&interval=1d&limit=15"
            respuesta = requests.get(url_completa, timeout=2.5)
            if respuesta.status_code == 200:
                break
            else:
                ultimo_error = f"HTTP {respuesta.status_code}"
        except Exception as e:
            ultimo_error = str(e)
            
    # Manejo de tiempos
    ahora_utc = datetime.utcnow()
    ahora_ve = ahora_utc - timedelta(hours=4)
    str_ve = ahora_ve.strftime("%I:%M:%S %p")
    
    if not respuesta or respuesta.status_code != 200:
        config.datos_mercado["ultima_actualizacion"] = f"❌ Error API: {ultimo_error}"
        config.datos_mercado["hora_venezuela"] = str_ve
        return

    try:
        datos = respuesta.json()
        precios_cierre = [float(dia[4]) for dia in datos]
        precio_actual = precios_cierre[-1]

        # Inicializar referencia si es la primera ejecución
        if precio_referencia is None:
            precio_referencia = precio_actual

        # Cálculo de variación %
        variacion = ((precio_actual - precio_referencia) / precio_referencia) * 100

        # Cálculo RSI
        ganancias, perdidas = [], []
        for i in range(1, len(precios_cierre)):
            diferencia = precios_cierre[i] - precios_cierre[i - 1]
            if diferencia > 0:
                ganancias.append(diferencia)
                perdidas.append(0)
            else:
                ganancias.append(0)
                perdidas.append(abs(diferencia))

        promedio_ganancias = sum(ganancias) / 14
        promedio_perdidas = sum(perdidas) / 14
        rsi = 100 if promedio_perdidas == 0 else 100 - (100 / (1 + (promedio_ganancias / promedio_perdidas)))

        estado_web = "Normal"
        if rsi < 30: estado_web = "💡 Sobrevendido"
        elif rsi > 70: estado_web = "⚠️ Sobrecomprado"

        # Actualizar datos globales
        config.datos_mercado.update({
            "precio_actual": precio_actual,
            "rsi": rsi,
            "variacion": variacion,
            "ultima_actualizacion": ahora_utc.strftime("%H:%M:%S UTC"),
            "hora_venezuela": str_ve
        })

        if not config.historial_analisis or config.historial_analisis[0]["precio"] != precio_actual:
            config.historial_analisis.insert(0, {
                "fecha": str_ve,
                "precio": precio_actual,
                "rsi": rsi,
                "estado": estado_web
            })
            if len(config.historial_analisis) > 10: config.historial_analisis.pop()

        # Alertas
        if rsi < 30 or rsi > 70:
            tipo = "SOBREVENDIDO" if rsi < 30 else "SOBRECOMPRADO"
            enviar_alerta_telegram(f"Bitcoin: ${precio_actual:,.2f} | RSI: {rsi:.2f} | {tipo}")

    except Exception as e:
        print(f"Error procesando: {e}")

def bucle_bot():
    while True:
        analizar_mercado()
        time.sleep(3)
        
