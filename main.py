import os
import json
import time
from threading import Thread
from flask import Flask, render_template_string, Response
import bot
import config

app = Flask(__name__)

@app.route("/api/stream")
def stream():
    def generador_datos():
        ultima_vez = None
        while True:
            # Esperar a que haya una actualización (con timeout para no bloquear)
            config.actualizacion_event.wait(timeout=1.0)
            # Limpiar el evento para la próxima
            config.actualizacion_event.clear()

            # Tomar los datos actuales
            actual = config.datos_mercado.get("ultima_actualizacion")
            if actual != ultima_vez and actual is not None:
                ultima_vez = actual
                yield f"data: {json.dumps({'datos': config.datos_mercado, 'historial': list(config.historial_analisis)})}\n\n"
            # Pequeña pausa para no saturar CPU
            time.sleep(0.01)
    return Response(generador_datos(), mimetype='text/event-stream')

@app.route("/")
def home():
    html_dashboard = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CryptoAlert Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-900 text-white min-h-screen p-4">
        <div class="max-w-4xl mx-auto">
            <div class="flex justify-between items-center mb-6">
                <h1 class="text-3xl font-bold text-indigo-400">CryptoAlert Dashboard</h1>
                <span class="bg-emerald-900 text-emerald-300 px-3 py-1 rounded-full text-xs font-bold">● Streaming en Vivo</span>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                <div class="bg-slate-800 p-6 rounded-2xl border border-slate-700">
                    <p class="text-slate-400 text-sm">Precio Bitcoin (BTC/USDT)</p>
                    <p id="btc-precio" class="text-2xl font-bold text-emerald-400">$0.00</p>
                </div>
                <div class="bg-slate-800 p-6 rounded-2xl border border-slate-700">
                    <p class="text-slate-400 text-sm">Variación (vs. día anterior)</p>
                    <p id="variacion-valor" class="text-2xl font-bold">0.00%</p>
                </div>
                <div class="bg-slate-800 p-6 rounded-2xl border border-slate-700">
                    <p class="text-slate-400 text-sm">RSI Actual (14 Días)</p>
                    <p id="rsi-valor" class="text-2xl font-bold text-amber-400">50.00</p>
                </div>
            </div>

            <div class="text-right mb-6 text-xs text-slate-500">
                <p>Estado del sistema: <span id="estado-sistema" class="text-indigo-300">Conectando...</span></p>
                <p>Hora local (Venezuela): <span id="hora-venezuela">--:--</span></p>
            </div>
            
            <div class="bg-slate-800 rounded-2xl p-6 border border-slate-700">
                <h2 class="text-lg font-bold mb-4">📋 Historial Reciente de Análisis</h2>
                <div id="historial-lista" class="divide-y divide-slate-700"></div>
            </div>
        </div>

        <script>
            const source = new EventSource('/api/stream');
            source.onmessage = (e) => {
                const data = JSON.parse(e.data);
                const d = data.datos;
                
                document.getElementById('btc-precio').innerText = '$' + d.precio_actual.toLocaleString();
                document.getElementById('rsi-valor').innerText = d.rsi.toFixed(2);
                document.getElementById('hora-venezuela').innerText = d.hora_venezuela;
                document.getElementById('estado-sistema').innerText = d.ultima_actualizacion;

                const varEl = document.getElementById('variacion-valor');
                const v = d.variacion;
                varEl.innerText = (v > 0 ? '+' : '') + v.toFixed(2) + '%';
                varEl.className = "text-2xl font-bold " + (v > 0 ? "text-emerald-400" : v < 0 ? "text-red-400" : "text-slate-400");

                const lista = document.getElementById('historial-lista');
                lista.innerHTML = data.historial.map(h => `
                    <div class="py-3 flex justify-between text-sm">
                        <span>${h.fecha}</span>
                        <span class="font-bold">BTC: $${h.precio.toLocaleString()}</span>
                        <span class="text-slate-400">${h.estado}</span>
                    </div>
                `).join('');
            };
            // Manejo de errores (reconexión automática)
            source.onerror = (e) => {
                document.getElementById('estado-sistema').innerText = '⚠️ Error de conexión, reintentando...';
                source.close();
                setTimeout(() => {
                    new EventSource('/api/stream');
                }, 3000);
            };
        </script>
    </body>
    </html>
    """
    return render_template_string(html_dashboard)

if __name__ == "__main__":
    Thread(target=bot.bucle_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
