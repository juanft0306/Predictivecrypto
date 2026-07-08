import os
from threading import Thread
from flask import Flask, render_template_string
import bot  # Importamos la lógica del bot
import config  # Importamos los datos compartidos

app = Flask(__name__)


@app.route("/")
def home():
    # Renderizado desacoplado: Lee directamente de config.py sin llamar a APIs externas
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
                    ● Bot Activo
                </span>
            </header>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                <div class="bg-slate-800 p-6 rounded-2xl shadow-xl border border-slate-700">
                    <p class="text-sm text-slate-400 uppercase tracking-wider font-semibold">Precio Bitcoin (BTC/USDT)</p>
                    <p class="text-4xl font-black text-emerald-400 mt-2">${{ "{:,.2f}".format(datos.precio_actual) }} USD</p>
                </div>
                
                <div class="bg-slate-800 p-6 rounded-2xl shadow-xl border border-slate-700">
                    <p class="text-sm text-slate-400 uppercase tracking-wider font-semibold">RSI Actual (14 Días)</p>
                    <div class="flex items-center justify-between mt-2">
                        <p class="text-4xl font-black {% if datos.rsi > 70 %}text-red-400{% elif datos.rsi < 30 %}text-cyan-400{% else %}text-amber-400{% endif %}">
                            {{ "{:.2f}".format(datos.rsi) }}
                        </p>
                        <span class="text-xs px-2 py-1 rounded font-bold {% if datos.rsi > 70 %}bg-red-500/20 text-red-400{% elif datos.rsi < 30 %}bg-cyan-500/20 text-cyan-400{% else %}bg-amber-500/20 text-amber-400{% endif %}">
                            {% if datos.rsi > 70 %}SOBRECOMPRA{% elif datos.rsi < 30 %}SOBREVENTA{% else %}NEUTRO{% endif %}
                        </span>
                    </div>
                </div>
            </div>

            <p class="text-xs text-slate-500 mb-8 text-right">Última revisión del bot: <span class="text-slate-300 font-medium">{{ datos.ultima_actualizacion }}</span></p>

            <div class="bg-slate-800 rounded-2xl shadow-xl border border-slate-700 overflow-hidden">
                <div class="px-6 py-4 border-b border-slate-700">
                    <h2 class="text-xl font-bold text-slate-200">📋 Historial Reciente de Análisis</h2>
                </div>
                <div class="divide-y divide-slate-700 max-h-96 overflow-y-auto">
                    {% if not historial %}
                        <p class="p-6 text-slate-400 text-center">Esperando el primer análisis del mercado...</p>
                    {% else %}
                        {% for registro in historial %}
                        <div class="p-4 flex flex-col sm:flex-row sm:items-center justify-between hover:bg-slate-750 transition-colors">
                            <div class="mb-2 sm:mb-0">
                                <span class="text-xs text-slate-400 block font-mono">{{ registro.fecha }}</span>
                                <span class="font-semibold text-slate-200">BTC: ${{ "{:,.2f}".format(registro.precio) }} USD</span>
                            </div>
                            <div class="flex items-center gap-4">
                                <span class="font-mono text-sm">RSI: <strong class="{% if registro.rsi > 70 %}text-red-400{% elif registro.rsi < 30 %}text-cyan-400{% else %}text-amber-400{% endif %}">{{ "{:.2f}".format(registro.rsi) }}</strong></span>
                                <span class="text-sm font-medium">{{ registro.estado }}</span>
                            </div>
                        </div>
                        {% endfor %}
                    {% endif %}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(
        html_dashboard, datos=config.datos_mercado, historial=config.historial_analisis
    )


if __name__ == "__main__":
    # 1. Creamos e iniciamos el hilo del bot de trading de fondo
    t_bot = Thread(target=bot.bucle_bot)
    t_bot.daemon = True
    t_bot.start()

    # 2. Corremos Flask en el hilo principal para Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    
