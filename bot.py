from datetime import datetime
import time
import requests
import config

def enviar_alerta_telegram(mensaje):
    url = f"https://api.telegram.org/bot{config.TOKEN_TELEGRAM}/sendMessage"
    payload = {"chat_id": config.CHAT_ID_TELEGRAM, "text": mensaje}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("❌ Error al enviar a Telegram:", e, flush=True)

def analizar_mercado():
    # Lista de servidores espejo de Binance para saltarnos bloqueos de IP
    endpoints = [
        "https://api.binance.com/api/v3/klines",
        "https://api1.binance.com/api/v3/klines",
        "https://api2.binance.com/api/v3/klines",
        "https://api3.binance.com/api/v3/klines"
    ]
    
    respuesta = None
    ultimo_error = ""
    
    # Intentar conectarse a cada uno hasta que uno funcione
    for url in endpoints:
        try:
            # Construimos la URL con los parámetros limpios
            url_completa = f"{url}?symbol=BTCUSDT&interval=1d&limit=15"
            respuesta = requests.get(url_completa, timeout=10)
            if respuesta.status_code == 200:
                break  # Éxito, salimos del bucle de servidores
            else:
                ultimo_error = f"HTTP {respuesta.status_code} ({url.split('//')[1].split('/')[0]})"
        except Exception as e:
            ultimo_error = str(e)
    
    # Si ninguno funcionó, reflejar el error en la interfaz web para saber qué pasa
    if not respuesta or respuesta.status_code != 200:
        ahora = datetime.now().strftime("%H:%M:%S")
        config.datos_mercado["ultima_actualizacion"] = f"❌ Error API: {ultimo_error} ({ahora})"
        print(f"❌ Fallaron todos los servidores de Binance. Motivo: {ultimo_error}", flush=True)
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

        # Guardar datos en la memoria compartida
        config.datos_mercado["precio_actual"] = precio_actual
        config.datos_mercado["rsi"] = rsi
        config.datos_mercado["ultima_actualizacion"] = ahora

        # Actualizar historial sin duplicar filas idénticas seguidas
        if not config.historial_analisis or config.historial_analisis[0]["precio"] != precio_actual:
            config.historial_analisis.insert(0, {
                "fecha": ahora,
                "precio": precio_actual,
                "rsi": rsi,
                "estado": estado_web
            })
            if len(config.historial_analisis) > 10:
                config.historial_analisis.pop()

        print(f"✅ Análisis exitoso a las {ahora}. BTC: ${precio_actual} | RSI: {rsi:.2f}", flush=True)

        # Disparador de alertas a Telegram
        if rsi < 30:
            reporte = f"=== ALERTAS CRIPTO ===\nBitcoin: ${precio_actual:,.2f} USD\nRSI: {rsi:.2f}\n--------------------\n💡 SEÑAL: SOBREVENDIDO."
            enviar_alerta_telegram(reporte)
        elif rsi > 70:
            reporte = f"=== ALERTAS CRIPTO ===\nBitcoin: ${precio_actual:,.2f} USD\nRSI: {rsi:.2f}\n--------------------\n⚠️ SEÑAL: SOBRECOMPRADO."
            enviar_alerta_telegram(reporte)

    except Exception as e:
        ahora = datetime.now().strftime("%H:%M:%S")
        config.datos_mercado["ultima_actualizacion"] = f"❌ Error Estructura JSON ({ahora})"
        print(f"❌ Error procesando la respuesta de Binance: {e}", flush=True)

def bucle_bot():
    print("🤖 Iniciando bucle de análisis secundario (Frecuencia: 30s)...", flush=True)
    while True:
        analizar_mercado()
        time.sleep(30)
          
