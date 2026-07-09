import os
import json
import time
from threading import Thread
from datetime import datetime
from flask import Flask, render_template, Response, jsonify, request
import bot
import config
import asistente

app = Flask(__name__)

# ============================================================
#  RUTAS PRINCIPALES
# ============================================================
@app.route("/")
def home():
    return render_template('index.html')

@app.route("/inversion")
def inversion():
    return render_template('inversion.html')

@app.route("/recomendaciones")
def recomendaciones():
    return render_template('recomendaciones.html')

@app.route("/asistente")
def asistente_page():
    return render_template('asistente.html')

# ============================================================
#  API STREAM (SSE)
# ============================================================
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
                    'moneda_seleccionada': config.moneda_seleccionada,
                    'recomendaciones': config.recomendaciones
                }
                yield f"data: {json.dumps(data)}\n\n"
            time.sleep(0.01)
    return Response(generador_datos(), mimetype='text/event-stream')

# ============================================================
#  API – ALERTAS
# ============================================================
@app.route("/api/enviar_alerta", methods=['POST'])
def enviar_alerta():
    try:
        bot.enviar_alerta_manual()
        return jsonify({"status": "ok", "mensaje": "Alerta enviada correctamente"})
    except Exception as e:
        config.logger.error(f"Error en /api/enviar_alerta: {e}")
        return jsonify({"status": "error", "mensaje": str(e)}), 500

@app.route("/api/enviar_recomendaciones", methods=['POST'])
def enviar_recomendaciones():
    try:
        mensaje = "📊 *RESUMEN DE RECOMENDACIONES*\n"
        mensaje += f"🕒 {datetime.now(config.ZONA_VE).strftime('%I:%M:%S %p')}\n\n"
        
        for symbol, rec in config.recomendaciones.items():
            nombre = config.NOMBRES_MONEDAS.get(symbol, symbol)
            abrev = symbol.replace('USDT', '')
            recom = rec.get("recomendacion", "Mantener")
            prob = rec.get("probabilidad", 50)
            precio = rec.get("indicadores", {}).get("precio", 0)
            rsi = rec.get("indicadores", {}).get("rsi", "--")
            variacion = rec.get("indicadores", {}).get("variacion", 0)
            
            emoji = "🟢" if recom == "Comprar" else "🔴" if recom == "Vender" else "🟡"
            mensaje += f"{emoji} *{nombre} ({abrev})*: {recom} ({prob}%)\n"
            mensaje += f"   Precio: ${precio:,.2f} | RSI: {rsi} | 24h: {variacion:+.2f}%\n\n"
        
        if not config.recomendaciones:
            mensaje += "⏳ No hay datos de recomendaciones aún.\n"
        
        bot.enviar_alerta_telegram(mensaje)
        return jsonify({"status": "ok", "mensaje": "Resumen de recomendaciones enviado"})
    except Exception as e:
        config.logger.error(f"Error en /api/enviar_recomendaciones: {e}")
        return jsonify({"status": "error", "mensaje": str(e)}), 500

# ============================================================
#  API – INVERSIÓN
# ============================================================
@app.route("/api/actualizar_inversion", methods=['POST'])
def actualizar_inversion():
    try:
        data = request.get_json()
        symbol = data.get('symbol', config.moneda_seleccionada)
        cantidad = float(data.get('cantidad', 0))
        capital_invertido = float(data.get('capital_invertido', 0))
        ganancia_deseada = float(data.get('ganancia_deseada', 0))
        
        if symbol not in config.inversiones:
            return jsonify({"status": "error", "mensaje": "Moneda no válida"}), 400
        if cantidad < 0 or capital_invertido < 0 or ganancia_deseada < 0:
            return jsonify({"status": "error", "mensaje": "Los valores no pueden ser negativos"}), 400
        
        config.inversiones[symbol]["cantidad"] = cantidad
        config.inversiones[symbol]["capital_invertido"] = capital_invertido
        config.inversiones[symbol]["ganancia_deseada"] = ganancia_deseada
        config.inversiones[symbol]["alcanzado"] = False
        
        config.guardar_inversiones()
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
        config.historial_analisis.clear()
        config.actualizacion_event.set()
        return jsonify({"status": "ok", "mensaje": f"Moneda cambiada a {symbol}"})
    except Exception as e:
        config.logger.error(f"Error en /api/cambiar_moneda: {e}")
        return jsonify({"status": "error", "mensaje": str(e)}), 500

# ============================================================
#  API – ASISTENTE
# ============================================================
@app.route("/api/asistente", methods=['POST'])
def preguntar_asistente():
    try:
        data = request.get_json()
        pregunta = data.get('pregunta', '')
        if not pregunta:
            return jsonify({"status": "error", "mensaje": "Pregunta vacía"}), 400
        
        respuesta = asistente.obtener_respuesta(pregunta)
        return jsonify({"status": "ok", "respuesta": respuesta})
    except Exception as e:
        config.logger.error(f"Error en /api/asistente: {e}")
        return jsonify({"status": "error", "mensaje": str(e)}), 500

@app.route("/api/preguntas_pendientes", methods=['GET'])
def obtener_preguntas_pendientes():
    try:
        pendientes = config.cargar_preguntas_pendientes()
        return jsonify({"status": "ok", "preguntas": pendientes})
    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

@app.route("/api/responder_pregunta", methods=['POST'])
def responder_pregunta():
    try:
        data = request.get_json()
        pregunta_texto = data.get('pregunta')
        respuesta = data.get('respuesta')
        if not pregunta_texto or not respuesta:
            return jsonify({"status": "error", "mensaje": "Faltan datos"}), 400
        
        # Guardar respuesta en el diccionario de respuestas para futuras consultas
        asistente.RESPUESTAS[pregunta_texto.lower()] = respuesta
        
        # Marcar como respondida en el archivo de pendientes
        pendientes = config.cargar_preguntas_pendientes()
        for p in pendientes:
            if p["pregunta"] == pregunta_texto and not p["respondida"]:
                p["respondida"] = True
                break
        with open(config.PREGUNTAS_FILE, "w", encoding="utf-8") as f:
            json.dump(pendientes, f, indent=2, ensure_ascii=False)
        
        return jsonify({"status": "ok", "mensaje": "Respuesta guardada"})
    except Exception as e:
        return jsonify({"status": "error", "mensaje": str(e)}), 500

# ============================================================
#  INICIO
# ============================================================
if __name__ == "__main__":
    Thread(target=bot.bucle_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
