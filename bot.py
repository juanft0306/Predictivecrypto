from datetime import datetime, timedelta
import time
import requests
import config

# ============================================================
#  CONSTANTES
# ============================================================
HISTORIAL_MAX = 5            # Número máximo de registros en el historial
INTERVALO_ACTUALIZACION = 60 # Segundos entre cada análisis

# Variable global para calcular la ganancia/pérdida (referencia inicial)
precio_referencia = None

# ============================================================
#  FUNCIONES AUXILIARES
# ============================================================
def enviar_alerta_telegram(mensaje):
    """Envía un mensaje al chat de Telegram si las credenciales están configuradas."""
    if not config.TOKEN_TELEGRAM or not config.CHAT_ID_TELEGRAM:
        print("⚠️  Token o Chat ID no configurados. No se enviará alerta.")
        return
    
    url = f"https://api.telegram.org/bot{config.TOKEN_TELEGRAM}/sendMessage"
    payload = {"chat_id": config.CHAT_ID_TELEGRAM, "text": mensaje}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"❌ Error al enviar mensaje a Telegram: {e}")

def obtener_precio():
    """
    Obtiene los datos de velas diarias de BTC/USDT desde Binance o MEXC.
    Retorna la lista de velas (JSON) o None si falla.
    """
    endpoints = [
        "https://api.binance.us/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=15",
        "https://api.mexc.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=15"
    ]
    
    for url in endpoints:
        try:
            respuesta = requests.get(url, timeout=5)
            if respuesta.status_code == 200:
                datos = respuesta.json()
                # Verificar que hay al menos 15 velas para tener 14 cambios
                if len(datos) >= 15:
                    return datos
                else:
                    print(f"⚠️  {url} devolvió solo {len(datos)} velas, se necesitan al menos 15.")
            else:
                print(f"⚠️  {url} respondió con código {respuesta.status_code}")
        except Exception as e:
            print(f"❌ Error al consultar {url}: {e}")
            continue
    return None

def analizar_mercado():
    """Obtiene datos, calcula RSI, variación y actualiza el estado global."""
    global precio_referencia
    
    datos = obtener_precio()
    
    if not datos:
        config.datos_mercado["ultima_actualizacion"] = "❌ Error API: Sin respuesta"
        return

    try:
        # Extraer precios de cierre (índice 4)
        precios = [float(dia[4]) for dia in datos]
        precio_actual = precios[-1]

        # Inicializar referencia si es la primera ejecución
        if precio_referencia is None:
            precio_referencia = precio_actual
            # Opcional: también podríamos fijar la referencia al precio anterior
            # para que la variación sea diaria. Aquí se mantiene como referencia inicial.

        # Cálculo de variación respecto al precio de referencia
        variacion = ((precio_actual - precio_referencia) / precio_referencia) * 100

        # --- Cálculo del RSI (14 periodos) ---
        # Necesitamos al menos 15 precios para tener 14 cambios
        if len(precios) < 15:
            # Si hay menos, no podemos calcular RSI correctamente
            rsi = 50.0  # valor neutro por defecto
        else:
            cambios = [precios[i] - precios[i-1] for i in range(1, len(precios))]
            # Tomamos los últimos 14 cambios (o los que haya si son menos)
            # Normalmente 14, pero por seguridad usamos los últimos 14 si hay más
            if len(cambios) >= 14:
                cambios_ultimos = cambios[-14:]
            else:
                cambios_ultimos = cambios  # caso poco probable, pero por si acaso

            ganancias = [c for c in cambios_ultimos if c > 0] or [0]
            perdidas = [abs(c) for c in cambios_ultimos if c < 0] or [0]

            # Promedios (usando la cantidad real de cambios)
            n = len(cambios_ultimos)
            promedio_ganancias = sum(ganancias) / n
            promedio_perdidas = sum(perdidas) / n

            if promedio_perdidas == 0:
                rsi = 100.0
            else:
                rs = promedio_ganancias / promedio_perdidas
                rsi = 100 - (100 / (1 + rs))

        # Hora actual en Venezuela (UTC-4)
        ahora_ve = (datetime.utcnow() - timedelta(hours=4)).strftime("%I:%M:%S %p")
        
        # Actualizar el diccionario central
        config.datos_mercado.update({
            "precio_actual": precio_actual,
            "rsi": rsi,
            "variacion": variacion,
            "ultima_actualizacion": datetime.utcnow().strftime("%H:%M:%S UTC"),
            "hora_venezuela": ahora_ve
        })

        # --- Actualizar historial (solo si cambió el precio) ---
        if (len(config.historial_analisis) == 0 or 
            config.historial_analisis[0]["precio"] != precio_actual):
            
            # Determinar estado según RSI
            if rsi < 30:
                estado_rsi = "Sobrevendido"
            elif rsi > 70:
                estado_rsi = "Sobrecomprado"
            else:
                estado_rsi = "Neutral"
            
            # Insertar al inicio
            config.historial_analisis.insert(0, {
                "fecha": ahora_ve,
                "precio": precio_actual,
                "estado": estado_rsi
            })
            
            # Mantener el límite
            if len(config.historial_analisis) > HISTORIAL_MAX:
                config.historial_analisis.pop()
            
            # (Opcional) Enviar alerta si RSI cruza umbrales
            # if rsi < 30 or rsi > 70:
            #     enviar_alerta_telegram(
            #         f"🚨 Alerta: BTC está {estado_rsi} (RSI={rsi:.2f})"
            #     )

    except Exception as e:
        print(f"❌ Error procesando datos: {e}")
        config.datos_mercado["ultima_actualizacion"] = f"❌ Error: {str(e)}"

def bucle_bot():
    """Bucle principal que ejecuta el análisis cada INTERVALO_ACTUALIZACION segundos."""
    print("🤖 Bot de análisis de mercado iniciado.")
    if not config.TOKEN_TELEGRAM or not config.CHAT_ID_TELEGRAM:
        print("⚠️  Credenciales de Telegram no configuradas. Las alertas no funcionarán.")
    else:
        print("✅ Credenciales de Telegram cargadas correctamente.")
    
    while True:
        try:
            analizar_mercado()
        except Exception as e:
            print(f"❌ Error en el bucle principal: {e}")
        time.sleep(INTERVALO_ACTUALIZACION)
