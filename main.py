import os
import json
import time
from threading import Thread
from flask import Flask, render_template, Response, jsonify
import bot
import config

app = Flask(__name__)

@app.route("/api/stream")
def stream():
    def generador_datos():
        ultima_vez = None
        while True:
            config.actualizacion_event.wait(timeout=1.0)
            config.actualizacion_event.clear()
            actual = config.datos_mercado.get("ultima_actualizacion")
            if actual != ultima_vez and actual is not None:
                ultima_vez = actual
                yield f"data: {json.dumps({'datos': config.datos_mercado, 'historial': list(config.historial_analisis)})}\n\n"
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

@app.route("/")
def home():
    return render_template('index.html')

if __name__ == "__main__":
    # Iniciar el bot en un hilo daemon
    Thread(target=bot.bucle_bot, daemon=True).start()
    # Puerto para Render o local
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
