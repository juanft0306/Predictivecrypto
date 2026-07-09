import json
import os
import requests
import re

ARCHIVO = "data/preguntas_respuestas.json"

def cargar_base():
    if not os.path.exists(ARCHIVO):
        # Base precargada
        base = {
            "preguntas": [
                {
                    "palabras": ["rsi", "qué significa", "indicador"],
                    "respuesta": "El RSI mide la velocidad y cambio de los movimientos de precio. Va de 0 a 100. Por debajo de 30: sobrevendido (posible subida). Por encima de 70: sobrecomprado (posible bajada)."
                },
                {
                    "palabras": ["macd", "qué es"],
                    "respuesta": "El MACD es un indicador de tendencia. Cuando la línea MACD cruza por encima de la señal, es señal alcista. Por debajo, bajista."
                },
                {
                    "palabras": ["precios", "datos", "de dónde"],
                    "respuesta": "Los precios se obtienen de la API pública de Binance cada 5 segundos."
                },
                {
                    "palabras": ["inversión", "configurar", "cómo"],
                    "respuesta": "Ve a 'Mi Inversión', selecciona la moneda, ingresa cantidad, capital y ganancia deseada. El sistema te alertará cuando alcances tu meta."
                },
                {
                    "palabras": ["consejos", "recomendaciones", "comprar", "vender"],
                    "respuesta": "Las recomendaciones se basan en múltiples indicadores (RSI, MACD, Bollinger, medias móviles). 'COMPRA FUERTE' es una señal alcista fuerte, 'VENTA FUERTE' es bajista."
                },
                {
                    "palabras": ["golden cross", "death cross"],
                    "respuesta": "Golden Cross: SMA50 cruza por encima de SMA200 (señal alcista). Death Cross: SMA50 cruza por debajo de SMA200 (señal bajista)."
                },
                {
                    "palabras": ["hola", "buenas", "saludos"],
                    "respuesta": "¡Hola! Soy Luz, tu asistente virtual. Pregúntame cualquier cosa sobre la aplicación o criptomonedas."
                }
            ]
        }
        os.makedirs(os.path.dirname(ARCHIVO), exist_ok=True)
        with open(ARCHIVO, "w", encoding="utf-8") as f:
            json.dump(base, f, indent=2, ensure_ascii=False)
        return base
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"preguntas": []}

def buscar_respuesta_local(texto):
    base = cargar_base()
    texto = texto.lower().strip()
    for item in base["preguntas"]:
        for palabra in item["palabras"]:
            if palabra.lower() in texto:
                return item["respuesta"]
    return None

def buscar_en_web(texto):
    try:
        # Usamos DuckDuckGo Instant Answer API (gratis, sin clave)
        url = "https://api.duckduckgo.com/"
        params = {
            "q": texto,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1
        }
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("AbstractText"):
                return data["AbstractText"]
            if data.get("Answer"):
                return data["Answer"]
            if data.get("Definition"):
                return data["Definition"]
    except:
        pass
    return None

def responder(texto):
    texto = texto.strip()
    if not texto:
        return "Por favor, escribe una pregunta."

    # Primero buscar en base local
    local = buscar_respuesta_local(texto)
    if local:
        return local

    # Luego buscar en web
    web = buscar_en_web(texto)
    if web:
        return web

    return "No tengo esa información en mi base de conocimiento. Intenta preguntar de otra forma o consulta la documentación."
