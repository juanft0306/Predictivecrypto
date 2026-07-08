from datetime import datetime
import time
import requests
import config  # Importamos la configuración global


def enviar_alerta_telegram(mensaje):
    url = f"https://api.telegram.org/bot{config.TOKEN_TELEGRAM}/sendMessage"
    payload = {"chat_id": config.CHAT_ID_TELEGRAM, "text": mensaje}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("Error aislado al enviar a Telegram:", e)


def analizar_mercado():
    url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=15"
    try:
        respuesta = requests.get(url, timeout=10)
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

        rsi = (
            100
            if promedio_perdidas == 0
            else 100 - (100 / (1 + (promedio_ganancias / promedio_perdidas)))
        )
        precio_actual = precios_cierre[-1]
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Configurar etiquetas visuales
        estado_web = "Normal"
        if rsi < 30:
            estado_web = "💡 Sobrevendido"
        elif rsi > 70:
            estado_web = "⚠️ Sobrecomprado"

        # Mutación directa de los datos en memoria compartida
        config.datos_mercado["precio_actual"] = precio_actual
        config.datos_mercado["rsi"] = rsi
        config.datos_mercado["ultima_actualizacion"] = ahora

        # Insertar registro en el historial evitando duplicados idénticos seguidos
        if (
            not config.historial_analisis
            or config.historial_analisis[0]["precio"] != precio_actual
        ):
            config.historial_analisis.insert(
                0,
                {
                    "fecha": ahora,
                    "precio": precio_actual,
                    "rsi": rsi,
                    "estado": estado_web,
                },
            )
            if len(config.historial_analisis) > 10:
                config.historial_analisis.pop()

        # Envío inteligente de alertas a Telegram
        if rsi < 30:
            reporte = f"=== ALERTAS CRIPTO ===\nBitcoin: ${precio_actual:,.2f} USD\nRSI: {rsi:.2f}\n--------------------\n💡 SEÑAL: SOBREVENDIDO. ¡Alta probabilidad de SUBIDA!"
            enviar_alerta_telegram(reporte)
        elif rsi > 70:
            reporte = f"=== ALERTAS CRIPTO ===\nBitcoin: ${precio_actual:,.2f} USD\nRSI: {rsi:.2f}\n--------------------\n⚠️ SEÑAL: SOBRECOMPRADO. Probabilidad de BAJA."
            enviar_alerta_telegram(reporte)
        else:
            print(f"Análisis ejecutado de fondo. RSI estable en {rsi:.2f}.")

    except Exception as e:
        print(f"Error controlado en el hilo del Bot (Binance): {e}")


def bucle_bot():
    print("Iniciando bucle de análisis secundario (Intervalo: 30s)...")
    while True:
        analizar_mercado()
        time.sleep(30)  # Frecuencia de actualización para la app web
