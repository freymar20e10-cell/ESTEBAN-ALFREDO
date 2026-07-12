"""
BT-7274 - Módulo de Internet
Búsquedas, clima, noticias, y utilidades web.
Con caché para no gastar llamadas innecesarias.
"""

import json
import urllib.request
import urllib.error
import urllib.parse
import webbrowser
from datetime import datetime
from xml.etree import ElementTree

from logger import log_action, log_error, log_api_call
from config import DEFAULT_CITY
from cache import get_cached, set_cached


# ═══════════════════════════════════════════
# CLIMA
# ═══════════════════════════════════════════

def get_weather(city: str = "") -> str:
    """
    Obtiene el clima actual usando wttr.in (gratis, sin API key).
    Si no se da ciudad, usa la de memoria o config.
    """
    if not city:
        # Intentar obtener de memoria
        try:
            from memory import get_preference
            city = get_preference("ciudad") or DEFAULT_CITY
        except Exception:
            city = DEFAULT_CITY
    try:
        # Verificar caché primero
        cached = get_cached("weather", city)
        if cached:
            return cached

        # Formato condensado en español
        city_encoded = urllib.parse.quote(city)
        url = f"https://wttr.in/{city_encoded}?format=j1"

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "BT-7274/1.0"}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        current = data.get("current_condition", [{}])[0]
        location = data.get("nearest_area", [{}])[0]

        city_name = location.get("areaName", [{"value": city}])[0]["value"]
        country = location.get("country", [{"value": ""}])[0]["value"]
        temp_c = current.get("temp_C", "?")
        feels_like = current.get("FeelsLikeC", "?")
        humidity = current.get("humidity", "?")
        description = current.get("lang_es", [{}])
        if description:
            desc_text = description[0].get("value", "")
        else:
            desc_text = current.get("weatherDesc", [{"value": ""}])[0]["value"]
        wind_kmph = current.get("windspeedKmph", "?")

        result = f"🌤️ Clima en {city_name}, {country}:\n\n"
        result += f"  🌡️ Temperatura: {temp_c}°C (sensación: {feels_like}°C)\n"
        result += f"  📝 Estado: {desc_text}\n"
        result += f"  💧 Humedad: {humidity}%\n"
        result += f"  💨 Viento: {wind_kmph} km/h\n"

        # Pronóstico de hoy
        weather_today = data.get("weather", [{}])[0]
        max_temp = weather_today.get("maxtempC", "?")
        min_temp = weather_today.get("mintempC", "?")
        result += f"  📊 Hoy: {min_temp}°C — {max_temp}°C\n"

        log_action(f"Consultó clima: {city_name}")
        set_cached("weather", city, result)
        return result

    except urllib.error.URLError as e:
        return f"❌ Error de conexión al consultar clima: {e.reason}"
    except Exception as e:
        return f"❌ Error al obtener clima: {e}"


def get_weather_simple(city: str = "") -> str:
    """Obtiene clima en formato simple de una línea."""
    if not city:
        try:
            from memory import get_preference
            city = get_preference("ciudad") or DEFAULT_CITY
        except Exception:
            city = DEFAULT_CITY
    try:
        city_encoded = urllib.parse.quote(city)
        url = f"https://wttr.in/{city_encoded}?format=%C+%t+%h+%w&lang=es"

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "BT-7274/1.0"}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            result = response.read().decode("utf-8").strip()

        return f"🌤️ {city}: {result}"
    except Exception as e:
        return f"❌ Error: {e}"


# ═══════════════════════════════════════════
# BÚSQUEDAS WEB
# ═══════════════════════════════════════════

def web_search(query: str) -> str:
    """
    Busca en DuckDuckGo y devuelve resultados resumidos.
    Usa la API instantánea de DuckDuckGo (gratis, sin key).
    """
    try:
        cached = get_cached("search", query)
        if cached:
            return cached

        query_encoded = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={query_encoded}&format=json&no_html=1&skip_disambig=1"

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "BT-7274/1.0"}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        results = []

        # Respuesta directa (Abstract)
        abstract = data.get("AbstractText", "")
        if abstract:
            source = data.get("AbstractSource", "")
            results.append(f"📖 {abstract}")
            if source:
                results.append(f"   Fuente: {source}")

        # Respuesta de tipo "Answer"
        answer = data.get("Answer", "")
        if answer:
            results.append(f"💡 {answer}")

        # Temas relacionados
        related = data.get("RelatedTopics", [])
        if related and not abstract:
            results.append("🔍 Resultados relacionados:\n")
            for i, topic in enumerate(related[:5]):
                if isinstance(topic, dict) and "Text" in topic:
                    text = topic["Text"][:150]
                    results.append(f"  {i+1}. {text}")

        if not results:
            # Si no hay resultados de la API, abrir en navegador
            search_url = f"https://duckduckgo.com/?q={query_encoded}"
            webbrowser.open(search_url)
            log_action(f"Búsqueda web (navegador): {query}")
            return f"🔍 No encontré un resumen rápido. Abrí la búsqueda en tu navegador: {query}"

        log_action(f"Búsqueda web: {query}")
        result_text = "\n".join(results)
        set_cached("search", query, result_text)
        return result_text

    except Exception as e:
        return f"❌ Error en búsqueda: {e}"


def open_url(url: str) -> str:
    """Abre una URL en el navegador predeterminado."""
    if not url.startswith("http"):
        url = "https://" + url

    webbrowser.open(url)
    log_action(f"Abrió URL: {url}")
    return f"🌐 Abriendo: {url}"


def search_and_open(query: str) -> str:
    """Busca algo en Google y abre los resultados."""
    query_encoded = urllib.parse.quote(query)
    url = f"https://www.google.com/search?q={query_encoded}"
    webbrowser.open(url)
    log_action(f"Búsqueda Google: {query}")
    return f"🔍 Buscando en Google: {query}"


# ═══════════════════════════════════════════
# NOTICIAS
# ═══════════════════════════════════════════

def get_news(category: str = "general") -> str:
    """
    Obtiene noticias recientes de Google News RSS (gratis, sin key).
    Categorías: general, tecnología, ciencia, deportes, entretenimiento
    """
    # RSS feeds de Google News en español
    feeds = {
        "general": "https://news.google.com/rss?hl=es&gl=US&ceid=US:es",
        "tecnología": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnpHZ0pWVXlnQVAB?hl=es&gl=US&ceid=US:es",
        "ciencia": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp0Y1RjU0FtVnpHZ0pWVXlnQVAB?hl=es&gl=US&ceid=US:es",
        "deportes": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdvU0FtVnpHZ0pWVXlnQVAB?hl=es&gl=US&ceid=US:es",
        "entretenimiento": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNREpxYW5RU0FtVnpHZ0pWVXlnQVAB?hl=es&gl=US&ceid=US:es",
    }

    url = feeds.get(category.lower(), feeds["general"])

    try:
        cached = get_cached("news", category.lower())
        if cached:
            return cached

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "BT-7274/1.0"}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read().decode("utf-8")

        root = ElementTree.fromstring(xml_data)
        channel = root.find("channel")

        if channel is None:
            return "❌ No pude obtener las noticias."

        items = channel.findall("item")[:8]  # Últimas 8 noticias

        if not items:
            return "📰 No se encontraron noticias."

        result = f"📰 Noticias ({category}):\n\n"
        for i, item in enumerate(items, 1):
            title = item.find("title")
            pub_date = item.find("pubDate")

            title_text = title.text if title is not None else "Sin título"
            date_text = ""
            if pub_date is not None and pub_date.text:
                try:
                    # Parsear fecha RSS
                    date_text = pub_date.text[:16]
                except Exception:
                    date_text = ""

            result += f"  {i}. {title_text}\n"
            if date_text:
                result += f"     📅 {date_text}\n"

        log_action(f"Consultó noticias: {category}")
        set_cached("news", category.lower(), result)
        return result

    except Exception as e:
        return f"❌ Error al obtener noticias: {e}"


# ═══════════════════════════════════════════
# UTILIDADES
# ═══════════════════════════════════════════

def get_datetime() -> str:
    """Obtiene la fecha y hora actual."""
    now = datetime.now()
    date_str = now.strftime("%A %d de %B de %Y")
    time_str = now.strftime("%H:%M:%S")
    return f"🕐 {date_str}\n   Hora: {time_str}"


def get_definition(word: str) -> str:
    """Busca la definición de una palabra (usa DictionaryAPI, gratis)."""
    try:
        cached = get_cached("definition", word.lower())
        if cached:
            return cached

        url = f"https://api.dictionaryapi.dev/api/v2/entries/es/{urllib.parse.quote(word)}"

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "BT-7274/1.0"}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        if isinstance(data, list) and len(data) > 0:
            entry = data[0]
            word_name = entry.get("word", word)
            meanings = entry.get("meanings", [])

            result = f"📚 Definición de '{word_name}':\n\n"
            for meaning in meanings[:3]:
                part = meaning.get("partOfSpeech", "")
                definitions = meaning.get("definitions", [])
                result += f"  ({part}):\n"
                for d in definitions[:2]:
                    result += f"    • {d.get('definition', '')}\n"

            set_cached("definition", word.lower(), result)
            return result
        else:
            return f"❌ No encontré definición para '{word}'."

    except urllib.error.HTTPError:
        return f"❌ No encontré definición para '{word}'."
    except Exception as e:
        return f"❌ Error: {e}"
