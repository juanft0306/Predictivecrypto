from datetime import datetime
import time
import requests
import config

def enviar_alerta_telegram(mensaje):
    url = f"https://api.telegram.org/bot{config.TOKEN_TELEGRAM}/sendMessage"
    payload = {"chat_id": config.CHAT_ID_TELEGRAM, "text": mensaje}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print("❌ Error al enviar a Telegram:", e, flush=True)

def analizar_mercado():
    endpoints = [
        "https://api.binance.us/api/v3/klines",
        "https://api.mexc.com/api/v3/klines"
    ]
    
    respuesta = None
    ultimo_error = ""
    
    for url in endpoints:
        try:
            url_completa = f"{url}?symbol=BTCUSDT&interval=1d&limit=15"
            # MEJORA 1: Reducimos el timeout a 2.5s para no congelar el bucle si la red está lenta
            respuesta = requests.get(url_completa, timeout=2.5)
            if respuesta.status_code == 200:
                break
            else:
                ultimo_error = f"HTTP {respuesta.status_code} ({url.split('//')[1].split('/')[0]})"
        except Exception as e:
            ultimo_error = str(e)
    
    if not respuesta or respuesta.status_code != 200:
        ahora = datetime.now().strftime("%H:%M:%S")
        config.datos_mercado["ultima_actualizacion"] = f"❌ Error API: {ultimo_error} ({ahora})"
        print(f"❌ Fallaron los servidores. Motivo: {ultimo_error}", flush=True)
        return

    try:
        datos = respuesta.json()
        precios_cierre = [float(dia[4]) for dia in datos]

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
        precio_actual = precios_cierre[-1]
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        estado_web = "Normal"
        if rsi < 30:
            estado_web = "💡 Sobrevendido"
        elif rsi > 70:
            estado_web = "⚠️ Sobrecomprado"

        config.datos_mercado["precio_actual"] = precio_actual
        config.datos_mercado["rsi"] = rsi
        config.datos_mercado["ultima_actualizacion"] = ahora

        if not config.historial_analisis or config.historial_analisis[0]["precio"] != precio_actual:
            config.historial_analisis.insert(0, {
                "fecha": ahora,
                "precio": precio_actual,
                "rsi": rsi,
                "estado": estado_web
            })
            if len(config.historial_analisis) > 10:
                config.historial_analisis.pop()

        print(f"📊 Análisis (10s) -> BTC: ${precio_actual} | RSI: {rsi:.2f}", flush=True)

        if rsi < 30:
            reporte = f"=== ALERTAS CRIPTO ===\nBitcoin: ${precio_actual:,.2f} USD\nRSI: {rsi:.2f}\n--------------------\n💡 SEÑAL: SOBREVENDIDO."
            enviar_alerta_telegram(reporte)
        elif rsi > 70:
            reporte = f"=== ALERTAS CRIPTO ===\nBitcoin: ${precio_actual:,.2f} USD\nRSI: {rsi:.2f}\n--------------------\n⚠️ SEÑAL: SOBRECOMPRADO."
            enviar_alerta_telegram(reporte)

    except Exception as e:
        ahora = datetime.now().strftime("%H:%M:%S")
        config.datos_mercado["ultima_actualizacion"] = f"❌ Error procesando JSON ({ahora})"
        print(f"❌ Error procesando los datos: {e}", flush=True)

def bucle_bot():
    print("🤖 Iniciando bucle de análisis secundario (Frecuencia estricta: 10s)...", flush=True)
    while True:
        # MEJORA 2: Tomamos una captura del tiempo exacto antes de empezar
        tiempo_inicio = time.time()
        
        analizar_mercado()
        
        # Calculamos cuánto tiempo tomó la ejecución del código y la red
        tiempo_transcurrido = time.time() - tiempo_inicio
        
        # El tiempo de espera será lo que falte para llegar a los 10 segundos
        tiempo_espera = 10 - tiempo_transcurrido
        
        # Control de seguridad: si la red tardó más de 10s, esperamos al menos 1s para no saturar
        if tiempo_espera < 1:
            tiempo_espera = 1
            
        time.sleep(tiempo_espera)
