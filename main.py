import os
import time
from threading import Thread
import requests
from flask import Flask

# === CONFIGURACIÓN DE FLASK (Para engañar a Render) ===
app = Flask(__name__)


@app.route("/")
def home():
    return "¡Bot de Alertas Cripto Activo y Corriendo!"


def run_flask():
    # Render asigna un puerto dinámico, lo leemos de las variables de entorno
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# === CONFIGURACIÓN DE TELEGRAM (SEGURA) ===
# Se leen desde las variables de entorno de Render. Si no existen, usan los valores por defecto.
TOKEN_TELEGRAM = os.environ.get(
    "TOKEN_TELEGRAM", "8113503204:AAF54TCwgjngtCyhYvWbCxDLMfyTrfTOB8"
)
CHAT_ID_TELEGRAM = os.environ.get("CHAT_ID_TELEGRAM", "5997657424")


def enviar_alerta_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage"
    payload = {"chat_id": CHAT_ID_TELEGRAM, "text": mensaje}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Error al enviar a Telegram:", e)


def analizar_mercado():
    url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=15"
    try:
        respuesta = requests.get(url)
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

        reporte = f"=== ALERTAS CRIPTO ===\nBitcoin: ${precio_actual:,.2f} USD\nRSI: {rsi:.2f}\n--------------------\n"

        if rsi < 30:
            reporte += "💡 SEÑAL: SOBREVENDIDO. ¡Alta probabilidad de SUBIDA!"
            enviar_alerta_telegram(reporte)
        elif rsi > 70:
            reporte += "⚠️ SEÑAL: SOBRECOMPRADO. Probabilidad de BAJA."
            enviar_alerta_telegram(reporte)
        else:
            print(f"Mercado analizado. RSI estable en {rsi:.2f}. No hay alertas.")

    except Exception as e:
        print("Error en el análisis:", e)


# === BUCLE PRINCIPAL DEL BOT ===
def bucle_bot():
    print("Iniciando bucle de análisis...")
    while True:
        analizar_mercado()
        # Se duerme por 4 horas (14400 segundos) antes de volver a revisar
        time.sleep(14400)


if __name__ == "__main__":
    # 1. Lanzamos el servidor Flask en un hilo secundario
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

    # 2. Corremos el bot en el hilo principal
    bucle_bot()
    
