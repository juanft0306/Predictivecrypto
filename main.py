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
            actual = config.datos_mercado.get("BTCUSDT", {}).get("ultima_actualizacion")
            if actual != ultima_vez and actual is not None:
                ultima_vez = actual
                data = {
                    'datos': config.datos_mercado,
                    'historial': list(config.historial_analisis),
                    'inversiones': config.inversiones,
                    'moneda_seleccionada': config.moneda_seleccionada
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
        symbol = data.get('symbol', config.moneda_seleccionada)
        cantidad = float(data.get('cantidad', 0))
        ganancia_deseada = float(data.get('ganancia_deseada', 0))
        
        if symbol not in config.inversiones:
            return jsonify({"status": "error", "mensaje": "Moneda no válida"}), 400
        if cantidad <= 0 or ganancia_deseada <= 0:
            return jsonify({"status": "error", "mensaje": "Los valores deben ser mayores a 0"}), 400
        
        # Obtener precio actual de la moneda
        precio_actual = config.datos_mercado.get(symbol, {}).get("precio_actual", 0)
        if precio_actual == 0:
            return jsonify({"status": "error", "mensaje": "No hay datos de precio para esta moneda"}), 400
        
        # Calcular capital invertido automáticamente
        capital_invertido = cantidad * precio_actual
        
        # Guardar datos
        config.inversiones[symbol]["cantidad"] = cantidad
        config.inversiones[symbol]["capital_invertido"] = capital_invertido
        config.inversiones[symbol]["ganancia_deseada"] = ganancia_deseada
        config.inversiones[symbol]["alcanzado"] = False
        
        # Forzar actualización SSE
        config.actualizacion_event.set()
        
        return jsonify({
            "status": "ok", 
            "mensaje": f"Inversión en {symbol} actualizada",
            "capital_invertido": capital_invertido,
            "monto_total_deseado": capital_invertido + ganancia_deseada
        })
    except Exception as e:
        config.logger.error(f"Error en /api/actualizar_inversion: {e}")
        return jsonify({"status": "error", "mensaje": str(e)}), 500

@app.route("/api/cambiar_moneda", methods=['POST'])
def cambiar_moneda():
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        if symbol not in config.MONEDAS:
            return jsonify({"status": "error", "mensaje": "Moneda no válida"}), 400
        config.moneda_seleccionada = symbol
        # Resetear historial para la nueva moneda
        config.historial_analisis.clear()
        config.actualizacion_event.set()
        return jsonify({"status": "ok", "mensaje": f"Moneda cambiada a {symbol}"})
    except Exception as e:
        config.logger.error(f"Error en /api/cambiar_moneda: {e}")
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
