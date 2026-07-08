from datetime import datetime
import time
import requests
import config  # Importamos nuestro archivo de configuración


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

        # Determinar estado visual
        estado_web = "Normal"
        if rsi < 30:
            estado_web = "💡 Sobrevendido"
        elif rsi > 70:
            estado_web = "⚠️ Sobrecomprado"

        # Actualizamos de forma segura el archivo config.py
        config.datos_mercado = {
            "precio_actual": precio_actual,
            "rsi": rsi,
            "ultima_actualizacion": ahora,
        }

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

        # Enviar alertas Telegram si el RSI rompe rangos
        reporte = f"=== ALERTAS CRIPTO ===\nBitcoin: ${precio_actual:,.2f} USD\nRSI: {rsi:.2f}\n--------------------\n"
        if rsi < 30:
            reporte += "💡 SEÑAL: SOBREVENDIDO. ¡Alta probabilidad de SUBIDA!"
            enviar_alerta_telegram(reporte)
        elif rsi > 70:
            reporte += "⚠️ SEÑAL: SOBRECOMPRADO. Probabilidad de BAJA."
            enviar_alerta_telegram(reporte)
        else:
            print(f"Mercado analizado de forma segura. RSI estable en {rsi:.2f}.")

    except Exception as e:
        # Si Binance falla, el bot no se rompe y Flask sigue vivo
        print(f"Error controlado en el análisis de mercado (Binance): {e}")


def bucle_bot():
    print("Iniciando bucle de análisis secundario...")
    analizar_mercado()  # Carga inicial al encender
    while True:
        time.sleep(14400)  # Revisa cada 4 horas
        analizar_mercado()
          
