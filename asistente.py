# =====================================================================
# INICIO - asistente.py
# =====================================================================
import config
import random
from datetime import datetime

# Diccionario de respuestas predefinidas
RESPUESTAS = {
    "hola": "¡Hola! Soy tu asistente cripto. ¿En qué puedo ayudarte?",
    "como estas": "Estoy funcionando al 100%, listo para ayudarte con tus inversiones.",
    "que es bitcoin": "Bitcoin es la primera criptomoneda descentralizada, creada en 2009 por Satoshi Nakamoto. Funciona con tecnología blockchain y su suministro está limitado a 21 millones de monedas.",
    "que es ethereum": "Ethereum es una plataforma descentralizada que permite ejecutar contratos inteligentes y aplicaciones descentralizadas (dApps). Su criptomoneda nativa es Ether (ETH).",
    "que es rsi": "El RSI (Relative Strength Index) es un indicador de momentum que mide la velocidad y magnitud de los movimientos de precio. Va de 0 a 100: por debajo de 30 indica sobreventa (posible compra) y por encima de 70 sobrecompra (posible venta).",
    "que es sma": "La SMA (Simple Moving Average) es un promedio de precios en un período determinado. Se usa para identificar tendencias: si el precio está por encima de la SMA, tendencia alcista; por debajo, bajista.",
    "que es macd": "MACD (Moving Average Convergence Divergence) es un indicador que muestra la relación entre dos medias móviles. Cuando la línea MACD cruza por encima de la señal, es señal alcista; por debajo, bajista.",
    "que significa comprar": "Comprar en trading significa adquirir un activo esperando que su precio suba para venderlo después y obtener ganancia. En nuestras recomendaciones, 'Comprar' indica una señal favorable para entrar.",
    "que significa vender": "Vender en trading significa deshacerte de un activo, ya sea para tomar ganancias o para evitar pérdidas. En nuestras recomendaciones, 'Vender' indica una señal para salir de la posición.",
    "que es binance": "Binance es el exchange de criptomonedas más grande del mundo por volumen de trading. Ofrece compra/venta de criptos, staking, futuros y más. Nosotros usamos su API para obtener precios.",
    "como funciona la app": "CryptoAlert monitorea 6 criptomonedas (BTC, ETH, BNB, SOL, XRP, TRX) usando datos de Binance. Analiza RSI, SMAs, MACD y te da recomendaciones con probabilidad de subida. También puedes configurar inversiones para recibir alertas cuando alcances tu meta.",
    "que es la probabilidad": "La probabilidad indica la fuerza de la señal de compra o venta en una escala del 0 al 100%. Se calcula combinando varios indicadores técnicos. Más de 70% es señal fuerte de compra, menos de 30% es señal de venta.",
    "que hacer si la recomendacion es comprar": "Si la recomendación es 'Comprar', significa que los indicadores son favorables para entrar. Puedes considerar comprar la moneda, pero siempre analiza otros factores y tu estrategia personal.",
    "que hacer si la recomendacion es vender": "Si la recomendación es 'Vender', significa que los indicadores sugieren salir de la posición. Puedes considerar vender para proteger tus ganancias o evitar pérdidas.",
    "que significa mantener": "'Mantener' significa que no hay una señal clara de compra o venta. Los indicadores están neutrales o mixtos. Es mejor esperar a que se defina una tendencia.",
    "que es la capitalizacion de mercado": "La capitalización de mercado es el valor total de una criptomoneda en circulación. Se calcula multiplicando el precio actual por el número de monedas en circulación.",
    "que es un exchange": "Un exchange es una plataforma donde se pueden comprar, vender e intercambiar criptomonedas. Ejemplos: Binance, Coinbase, Kraken.",
    "que es una wallet": "Una wallet o billetera es un software o dispositivo que almacena tus claves privadas y te permite gestionar tus criptomonedas. Puede ser caliente (online) o fría (offline).",
    "que es el staking": "El staking es el proceso de mantener criptomonedas en una wallet para apoyar la red de una blockchain y recibir recompensas a cambio, similar a los intereses en un banco.",
    "que es la blockchain": "Blockchain es una tecnología de registro distribuido que permite almacenar datos en bloques encadenados de forma segura, descentralizada e inmutable. Es la base de todas las criptomonedas.",
    "que es una altcoin": "Altcoin es cualquier criptomoneda que no sea Bitcoin. Ejemplos: Ethereum, Solana, XRP, TRON, etc.",
    "que es el trading": "El trading es la compra y venta de activos financieros con el objetivo de obtener ganancias a corto o mediano plazo. Se basa en el análisis técnico y fundamental.",
    "que es la inversion a largo plazo": "Invertir a largo plazo significa comprar un activo y mantenerlo durante años, esperando que su valor aumente con el tiempo. También conocido como 'HODL' en el mundo cripto.",
    "que es el apalancamiento": "El apalancamiento es usar dinero prestado para aumentar el tamaño de una operación. Amplifica tanto ganancias como pérdidas. Es muy riesgoso.",
    "que es el stop loss": "El stop loss es una orden de venta automática que se ejecuta cuando el precio baja a un nivel determinado, para limitar las pérdidas.",
    "que es el take profit": "El take profit es una orden de venta automática que se ejecuta cuando el precio sube a un nivel determinado, para asegurar las ganancias.",
    "que son los fundamentales": "El análisis fundamental evalúa el valor intrínseco de un activo basándose en factores económicos, financieros y otros datos cualitativos. En cripto, incluye adopción, desarrollo, equipo, etc.",
    "que es la volatilidad": "La volatilidad es la medida de la variación del precio de un activo en el tiempo. Alta volatilidad = grandes movimientos de precio (más riesgo y oportunidad).",
    "que es un bull run": "Un bull run es un período prolongado de aumento de precios en el mercado, caracterizado por optimismo y confianza de los inversores.",
    "que es un bear market": "Un bear market es un período prolongado de caída de precios, caracterizado por pesimismo y miedo en el mercado.",
    "cuanto cuesta bitcoin": "El precio de Bitcoin varía constantemente. Puedes verlo en el dashboard de CryptoAlert en tiempo real.",
    "que monedas sigue la app": "CryptoAlert sigue 6 monedas: Bitcoin (BTC), Ethereum (ETH), BNB Chain (BNB), Solana (SOL), XRP (XRP) y TRON (TRX).",
}

def obtener_respuesta(pregunta):
    """
    Busca una respuesta para la pregunta del usuario.
    Si no encuentra coincidencia, guarda la pregunta como pendiente.
    """
    pregunta_lower = pregunta.lower().strip()
    
    # Buscar coincidencia exacta o parcial
    for clave, respuesta in RESPUESTAS.items():
        if clave in pregunta_lower:
            return respuesta
    
    # Si no encuentra, guardar pregunta pendiente
    fecha = datetime.now(config.ZONA_VE).strftime("%Y-%m-%d %H:%M:%S")
    config.guardar_pregunta_pendiente(pregunta, fecha)
    
    return "🤔 No tengo una respuesta para esa pregunta aún. La he guardado para que el equipo la revise y te responda pronto. ¡Gracias por ayudarme a aprender!"
# =====================================================================
# FIN - asistente.py
# =====================================================================
