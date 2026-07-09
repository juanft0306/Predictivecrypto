import os
import json
import time
from threading import Thread
from flask import Flask, render_template, Response, jsonify, request
import bot
import config
from inversion import cargar, guardar, inicializar, actualizar, limpiar, obtener_historial
from asistente import responder
from utils import hora_ve

app = Flask(__name__)

# Inicializar inversiones
inicializar()
config.moneda_seleccionada = "BTCUSDT"

@app.route("/api/stream")
def stream():
    def generador():
        ultima = None
        while True:
            config.actualizacion_event.wait(timeout=0.5)
            config.actualizacion_event.clear()
            actual = config.datos_mercado.get("BTCUSDT", {}).get("ultima_actualizacion")
            if actual != ultima and actual is not None:
                ultima = actual
                data = {
                    'datos': config.datos_mercado,
                    'historial': config.historial_precios[-20:],
                    'inversiones': cargar(),
                    'moneda_seleccionada': config.moneda_seleccionada,
                    'hora_actual': hora_ve()
                }
                yield f"data: {json.dumps(data)}\n\n"
            time.sleep(0.01)
    return Response(generador(), mimetype='text/event-stream')

@app.route("/api/enviar_alerta", methods=['POST'])
def enviar_alerta():
    try:
        bot.enviar_telegram("📊 *Alerta manual* - Resumen general enviado desde la app.")
        return jsonify({"status": "ok", "mensaje": "Alerta enviada"})
    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

@app.route("/api/actualizar_inversion", methods=['POST'])
def api_actualizar_inversion():
    try:
        data = request.get_json()
        symbol = data.get('symbol', config.moneda_seleccionada)
        cantidad = float(data.get('cantidad', 0))
        capital = float(data.get('capital', 0))
        ganancia = float(data.get('ganancia_deseada', 0))
        if cantidad <= 0 or capital <= 0 or ganancia <= 0:
            return jsonify({"status": "error", "mensaje": "Todos los valores deben ser > 0"}), 400
        actualizar(symbol, cantidad, capital, ganancia)
        config.actualizacion_event.set()
        return jsonify({"status": "ok", "mensaje": f"Inversión en {symbol} actualizada"})
    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

@app.route("/api/limpiar_inversion", methods=['POST'])
def api_limpiar_inversion():
    try:
        data = request.get_json()
        symbol = data.get('symbol', config.moneda_seleccionada)
        limpiar(symbol)
        config.actualizacion_event.set()
        return jsonify({"status": "ok", "mensaje": "Inversión limpiada"})
    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

@app.route("/api/cambiar_moneda", methods=['POST'])
def api_cambiar_moneda():
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        if symbol not in config.MONEDAS:
            return jsonify({"status": "error", "mensaje": "Moneda no válida"}), 400
        config.moneda_seleccionada = symbol
        config.historial_precios.clear()
        config.actualizacion_event.set()
        return jsonify({"status": "ok", "mensaje": f"Moneda cambiada a {symbol}"})
    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

@app.route("/api/asistente", methods=['POST'])
def api_asistente():
    try:
        data = request.get_json()
        pregunta = data.get('pregunta', '')
        respuesta = responder(pregunta)
        return jsonify({"status": "ok", "respuesta": respuesta})
    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/inversion")
def inversion():
    return render_template('inversion.html')

@app.route("/consejos")
def consejos():
    return render_template('consejos.html')

@app.route("/historial")
def historial():
    return render_template('historial.html')

@app.route("/asistente")
def asistente():
    return render_template('asistente.html')

if __name__ == "__main__":
    Thread(target=bot.bucle, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
