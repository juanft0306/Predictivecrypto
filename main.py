import os
import json
import time
from threading import Thread
from flask import Flask, render_template_string, Response
import bot
import config

app = Flask(__name__)

# NUEVO: Endpoint de Streaming en Tiempo Real (Server-Sent Events)
@app.route("/api/stream")
def stream():
    def generador_datos():
        ultima_vez = None
        while True:
            actual = config.datos_mercado.get("ultima_actualizacion")
            # Solo envía datos a tu teléfono si detecta que el bot consiguió precios nuevos
            if actual != ultima_vez and actual is not None:
                ultima_vez = actual
                paquete = {
                    "datos": config.datos_mercado,
                    "historial": list(config.historial_analisis)
                }
                # El formato "data: {json}\n\n" es estricto para que el navegador lo entienda
                yield f"data: {json.dumps(paquete)}\n\n"
            time.sleep(0.5) # El servidor revisa su propia memoria interna cada 0.5s
            
    return Response(generador_datos(), mimetype='text/event-stream')

@app.route("/")
def home():
    html_dashboard = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard Cripto Alertas</title>
        <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    </head>
    <body class="bg-slate-900 text-white font-sans min-h-screen">
        <div class="container mx-auto px-4 py-8 max-w-4xl">
            <header class="flex justify-between items-center border-b border-slate-700 pb-4 mb-8">
                <h1 class="text-3xl font-extrabold text-indigo-400">📊 CryptoAlert Dashboard</h1>
                <span class="bg-green-500/20 text-green-400 px-3 py-1 rounded-full text-sm font-semibold animate-pulse">
                    ● Streaming en Vivo
                </span>
            </header>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                <div class="bg-slate-800 p-6 rounded-2xl shadow-xl border border-slate-700">
                    <p class="text-sm text-slate-400 uppercase tracking-wider font-semibold">Precio Bitcoin (BTC/USDT)</p>
                    <p id="btc-precio" class="text-4xl font-black text-emerald-400 mt-2 transition-all duration-300">Cargando...</p>
                </div>
                
                <div class="bg-slate-800 p-6 rounded-2xl shadow-xl border border-slate-700">
                    <p class="text-sm text-slate-400 uppercase tracking-wider font-semibold">RSI Actual (14 Días)</p>
                    <div class="flex items-center justify-between mt-2">
                        <p id="rsi-valor" class="text-4xl font-black text-amber-400 transition-all duration-300">--.--</p>
                        <span id="rsi-badge" class="text-xs px-2 py-1 rounded font-bold bg-amber-500/20 text-amber-400">CONECTANDO</span>
                    </div>
                </div>
            </div>

            <p class="text-xs text-slate-500 mb-8 text-right tracking-tight">
                Estado del sistema: <span id="actualizacion-tiempo" class="text-slate-300 font-medium animate-pulse">Abriendo túnel SSE...</span>
            </p>

            <div class="bg-slate-800 rounded-2xl shadow-xl border border-slate-700 overflow-hidden">
                <div class="px-6 py-4 border-b border-slate-700 flex justify-between items-center">
                    <h2 class="text-xl font-bold text-slate-200">📋 Historial de Análisis</h2>
                </div>
                <div id="historial-lista" class="divide-y divide-slate-700 max-h-96 overflow-y-auto">
                    <p class="p-6 text-slate-400 text-center italic">Esperando paquete de datos del servidor...</p>
                </div>
            </div>
        </div>

        <script>
            function network_clean(d) {
                return {
                    precio_actual: d.precio_actual || 0,
                    rsi: d.rsi || 50.0,
                    ultima_actualizacion: d.ultima_actualizacion || "Conectado"
                };
            }

            // MAGIA DE TIEMPO REAL: Abre un túnel permanente con tu servidor Render
            const origenEventos = new EventSource('/api/stream');

            origenEventos.onmessage = function(evento) {
                // Se ejecuta exactamente en el milisegundo en que llega un nuevo dato
                const resultado = JSON.parse(evento.data);
                const datos = network_clean(resultado.datos);
                const historial = resultado.historial;

                if (datos.precio_actual > 0) {
                    const formatoMoneda = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });
                    document.getElementById('btc-precio').innerText = formatoMoneda.format(datos.precio_actual) + " USD";
                }
                
                document.getElementById('rsi-valor').innerText = datos.rsi.toFixed(2);
                document.getElementById('actualizacion-tiempo').innerText = datos.ultima_actualizacion;
                document.getElementById('actualizacion-tiempo').classList.remove('animate-pulse');

                const rsiVal = datos.rsi;
                const rsiBadge = document.getElementById('rsi-badge');
                const rsiTexto = document.getElementById('rsi-valor');
                
                if (rsiVal > 70) {
                    rsiTexto.className = "text-4xl font-black text-red-400 transition-all duration-300";
                    rsiBadge.className = "text-xs px-2 py-1 rounded font-bold bg-red-500/20 text-red-400";
                    rsiBadge.innerText = "SOBRECOMPRA";
                } else if (rsiVal < 30) {
                    rsiTexto.className = "text-4xl font-black text-cyan-400 transition-all duration-300";
                    rsiBadge.className = "text-xs px-2 py-1 rounded font-bold bg-cyan-500/20 text-cyan-400";
                    rsiBadge.innerText = "SOBREVENTA";
                } else {
                    rsiTexto.className = "text-4xl font-black text-amber-400 transition-all duration-300";
                    rsiBadge.className = "text-xs px-2 py-1 rounded font-bold bg-amber-500/20 text-amber-400";
                    rsiBadge.innerText = "NEUTRO";
                }

                const listaHistorial = document.getElementById('historial-lista');
                if (historial.length > 0) {
                    let htmlContenido = "";
                    historial.forEach(reg => {
                        const pReg = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(reg.precio);
                        let colorRsi = reg.rsi > 70 ? 'text-red-400' : (reg.rsi < 30 ? 'text-cyan-400' : 'text-amber-400');
                        
                        htmlContenido += `
                        <div class="p-4 flex flex-col sm:flex-row sm:items-center justify-between hover:bg-slate-750 transition-colors">
                            <div class="mb-2 sm:mb-0">
                                <span class="text-xs text-slate-400 block font-mono font-bold">${reg.fecha}</span>
                                <span class="font-bold text-slate-200">BTC: ${pReg} USD</span>
                            </div>
                            <div class="flex items-center gap-4">
                                <span class="font-mono text-sm">RSI: <strong class="${colorRsi}">${reg.rsi.toFixed(2)}</strong></span>
                                <span class="text-sm font-medium text-slate-400">${reg.estado}</span>
                            </div>
                        </div>`;
                    });
                    listaHistorial.innerHTML = htmlContenido;
                }
            };

            origenEventos.onerror = function() {
                document.getElementById('actualizacion-tiempo').innerText = "Reconectando con el servidor...";
                document.getElementById('actualizacion-tiempo').classList.add('animate-pulse');
            };
        </script>
    </body>
    </html>
    """
    return render_template_string(html_dashboard)

if __name__ == "__main__":
    t_bot = Thread(target=bot.bucle_bot)
    t_bot.daemon = True
    t_bot.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
