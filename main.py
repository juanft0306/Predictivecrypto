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
            actual = config.datos_mercado.get("ultima_actualizacion")
            if actual != ultima_vez and actual is not None:
                ultima_vez = actual
                yield f"data: {json.dumps({'datos': config.datos_mercado, 'historial': list(config.historial_analisis)})}\n\n"
            time.sleep(0.5)
    return Response(generador_datos(), mimetype='text/event-stream')

@app.route("/")
def home():
    html_dashboard = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Crypto Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-900 text-white min-h-screen p-4">
        <div class="max-w-4xl mx-auto">
            <h1 class="text-3xl font-bold mb-6 text-indigo-400">📊 Dashboard BTC</h1>
            
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                <div class="bg-slate-800 p-6 rounded-2xl border border-slate-700">
                    <p class="text-slate-400 text-sm">Precio Actual</p>
                    <p id="btc-precio" class="text-2xl font-bold text-emerald-400">--</p>
                </div>
                <div class="bg-slate-800 p-6 rounded-2xl border border-slate-700">
                    <p class="text-slate-400 text-sm">Variación</p>
                    <p id="variacion-valor" class="text-2xl font-bold">0.00%</p>
                </div>
                <div class="bg-slate-800 p-6 rounded-2xl border border-slate-700">
                    <p class="text-slate-400 text-sm">RSI</p>
                    <p id="rsi-valor" class="text-2xl font-bold text-amber-400">--</p>
                </div>
            </div>

            <div class="text-right mb-6 text-xs text-slate-500">
                <p>Hora Local (VE): <span id="hora-venezuela" class="text-indigo-300">--:--</span></p>
            </div>
            
            <div id="historial-lista" class="bg-slate-800 rounded-2xl p-4 divide-y divide-slate-700"></div>
        </div>

        <script>
            const source = new EventSource('/api/stream');
            source.onmessage = (e) => {
                const data = JSON.parse(e.data);
                const d = data.datos;
                
                // Actualizar valores
                document.getElementById('btc-precio').innerText = '$' + d.precio_actual.toLocaleString();
                document.getElementById('rsi-valor').innerText = d.rsi.toFixed(2);
                document.getElementById('hora-venezuela').innerText = d.hora_venezuela;

                // Actualizar Variación
                const varEl = document.getElementById('variacion-valor');
                const v = d.variacion;
                varEl.innerText = (v > 0 ? '+' : '') + v.toFixed(2) + '%';
                varEl.className = "text-2xl font-bold " + (v > 0 ? "text-emerald-400" : v < 0 ? "text-red-400" : "text-slate-400");

                // Actualizar Historial
                const lista = document.getElementById('historial-lista');
                lista.innerHTML = data.historial.map(h => `
                    <div class="py-3 flex justify-between text-sm">
                        <span>${h.fecha}</span>
                        <span class="font-bold">$${h.precio.toLocaleString()}</span>
                        <span>${h.estado}</span>
                    </div>
                `).join('');
            };
        </script>
    </body>
    </html>
    """
    return render_template_string(html_dashboard)

if __name__ == "__main__":
    Thread(target=bot.bucle_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
    """
    
