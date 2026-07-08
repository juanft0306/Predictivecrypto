import os
import json
import time
from threading import Thread
from flask import Flask, render_template, Response, jsonify, request
import bot
import config

app = Flask(__name__)

@app.route("/api/stream")
def stream():
    def generador_datos():
        ultima_vez = None
        while True:
            config.actualizacion_event.wait(timeout=0.5)
            config.actualizacion_event.clear()
            actual = config.datos_mercado.get("ultima_actualizacion")
            if actual != ultima_vez and actual is not None:
                ultima_vez = actual
                # Enviamos también los datos de inversión
                data = {
                    'datos': config.datos_mercado,
                    'historial': list(config.historial_analisis),
                    'inversion': {
                        'cantidad_btc': config.cantidad_btc,
                        'precio_objetivo': config.precio_objetivo,
                        'objetivo_alcanzado': config.objetivo_alcanzado
                    }
                }
                yield f"data: {json.dumps(data)}\n\n"
            time.sleep(0.01)
    return Response(generador_datos(), mimetype='text/event-stream')

@app.route("/api/enviar_alerta", methods=['POST'])
def enviar_alerta():
    try:
        bot.enviar_alerta_manual()
        return jsonify({"status": "ok", "mensaje": "Alerta enviada correctamente"})
    except Exception as e:
        config.logger.error(f"Error en /api/enviar_alerta: {e}")
        return jsonify({"status": "error", "mensaje": str(e)}), 500

@app.route("/api/actualizar_inversion", methods=['POST'])
def actualizar_inversion():
    try:
        data = request.get_json()
        cantidad = float(data.get('cantidad_btc', 0))
        objetivo = float(data.get('precio_objetivo', 0))
        if cantidad < 0 or objetivo < 0:
            return jsonify({"status": "error", "mensaje": "Los valores deben ser positivos"}), 400
        config.cantidad_btc = cantidad
        config.precio_objetivo = objetivo
        config.objetivo_alcanzado = False   # Resetear notificación
        # Forzar actualización SSE
        config.actualizacion_event.set()
        return jsonify({"status": "ok", "mensaje": "Datos de inversión actualizados"})
    except Exception as e:
        config.logger.error(f"Error en /api/actualizar_inversion: {e}")
        return jsonify({"status": "error", "mensaje": str(e)}), 500

@app.route("/")
def home():
    return render_template('index.html')

@app.route("/inversion")
def inversion():
    return render_template('inversion.html')

if __name__ == "__main__":
    Thread(target=bot.bucle_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
