from datetime import datetime, timedelta
import time
import requests
import config

# Variable global para calcular la ganancia/pérdida
precio_referencia = None

def enviar_alerta_telegram(mensaje):
    if not config.TOKEN_TELEGRAM or config.TOKEN_TELEGRAM == "TU_TOKEN_AQUI":
        return
    url = f"https://api.telegram.org/bot{config.TOKEN_TELEGRAM}/sendMessage"
    payload = {"chat_id": config.CHAT_ID_TELEGRAM, "text": mensaje}
    try:
        requests.post(url, json=payload, timeout=5)
    except: 
        pass

def obtener_precio():
    # Intentamos Binance, si falla, intentamos MEXC
    endpoints = [
        "https://api.binance.us/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=15",
        "https://api.mexc.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=15"
    ]
    
    for url in endpoints:
        try:
            respuesta = requests.get(url, timeout=5)
            if respuesta.status_code == 200:
                return respuesta.json()
        except Exception:
            continue
    return None

def analizar_mercado():
    global precio_referencia
    
    datos = obtener_precio()
    
    if not datos:
        config.datos_mercado["ultima_actualizacion"] = "❌ Error API: Sin respuesta"
        return

    try:
        precios = [float(dia[4]) for dia in datos]
        precio_actual = precios[-1]

        # Inicializar referencia
        if precio_referencia is None: 
            precio_referencia = precio_actual

        # Cálculo de variación
        variacion = ((precio_actual - precio_referencia) / precio_referencia) * 100

        # RSI (14 periodos)
        cambios = [precios[i] - precios[i-1] for i in range(1, len(precios))]
        ganancias = [c for c in cambios if c > 0] or [0]
        perdidas = [abs(c) for c in cambios if c < 0] or [0]
        
        promedio_ganancias = sum(ganancias) / 14
        promedio_perdidas = sum(perdidas) / 14
        
        if promedio_perdidas == 0:
            rsi = 100
        else:
            rs = promedio_ganancias / promedio_perdidas
            rsi = 100 - (100 / (1 + rs))

        # Hora y estado
        ahora_ve = (datetime.utcnow() - timedelta(hours=4)).strftime("%I:%M:%S %p")
        
        # Actualizar estado
        config.datos_mercado.update({
            "precio_actual": precio_actual,
            "rsi": rsi,
            "variacion": variacion,
            "ultima_actualizacion": datetime.utcnow().strftime("%H:%M:%S UTC"),
            "hora_venezuela": ahora_ve
        })

        # Historial
        if len(config.historial_analisis) == 0 or config.historial_analisis[0]["precio"] != precio_actual:
            estado_rsi = "Neutral"
            if rsi < 30: estado_rsi = "Sobrevendido"
            elif rsi > 70: estado_rsi = "Sobrecomprado"
            
            config.historial_analisis.insert(0, {"fecha": ahora_ve, "precio": precio_actual, "estado": estado_rsi})
            if len(config.historial_analisis) > 5: config.historial_analisis.pop()

    except Exception as e:
        print(f"Error procesando datos: {e}")

def bucle_bot():
    while True:
        analizar_mercado()
        time.sleep(60) # Espera 60 segundos para evitar bloqueos
        
