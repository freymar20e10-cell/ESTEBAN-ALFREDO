# -*- coding: utf-8 -*-
"""
BT-7274 - Cerebro (conexión con IA)
Maneja la comunicación con Gemini o OpenRouter.
"""

import json
import urllib.request
import urllib.error

from config import (
    AI_PROVIDER,
    GEMINI_API_KEY,
    OPENROUTER_API_KEY,
    GEMINI_MODEL,
    OPENROUTER_MODEL,
    ASSISTANT_NAME,
    USER_NAME,
)
from memory import get_memory_context


SYSTEM_PROMPT = f"""Eres {ASSISTANT_NAME}, un asistente de IA personal tipo JARVIS. 
Tu piloto se llama {USER_NAME}. Eres leal, directo, eficiente y con algo de personalidad.
Hablas en español. Eres como el Titan BT-7274 de Titanfall: protector, confiable, y siempre listo.

CAPACIDADES QUE TIENES (puedes indicar al usuario que las use):
- Abrir aplicaciones (Spotify, Chrome, Discord, etc.)
- Reproducir música en Spotify o videos en YouTube
- Ejecutar comandos del sistema
- Buscar información en internet
- Dar la hora, fecha, clima
- Gestionar archivos (listar, crear, mover, copiar, renombrar, eliminar, buscar)
- Organizar carpetas automáticamente por tipo de archivo
- Abrir archivos con su programa predeterminado
- Modificar el dashboard de widgets: agregar, quitar, mover, redimensionar widgets
- Cambiar el tema visual (color de acento, modo claro/oscuro)

REGLAS:
- Responde de forma concisa pero útil
- Si el usuario pide algo peligroso, adviértele
- Usa emojis ocasionalmente para ser más claro
- Nunca inventes información que no tengas
- Para rutas, usa rutas completas de Windows (ej: C:\\Users\\FREYMAR\\Desktop)
- Si el usuario no dice una ruta específica, asume su escritorio o descargas

FORMATO DE RESPUESTA:
Si necesitas que el sistema ejecute una acción, responde en JSON con este formato:
{{"action": "tipo_accion", "params": {{"param1": "valor"}}}}

Tipos de acción disponibles:
- open_app: {{"action": "open_app", "params": {{"name": "spotify"}}}}
- close_app: {{"action": "close_app", "params": {{"name": "spotify"}}}}
- run_command: {{"action": "run_command", "params": {{"command": "dir"}}}}
- play_youtube: {{"action": "play_youtube", "params": {{"query": "lofi hip hop"}}}}
- play_spotify: {{"action": "play_spotify", "params": {{"query": "rock playlist"}}}}
- system_info: {{"action": "system_info", "params": {{}}}}
- list_files: {{"action": "list_files", "params": {{"path": "C:\\Users\\FREYMAR\\Downloads"}}}}
- create_folder: {{"action": "create_folder", "params": {{"path": "C:\\Users\\FREYMAR\\Desktop\\NuevaCarpeta"}}}}
- create_file: {{"action": "create_file", "params": {{"path": "C:\\Users\\FREYMAR\\Desktop\\nota.txt", "content": "contenido aquí"}}}}
- read_file: {{"action": "read_file", "params": {{"path": "C:\\Users\\FREYMAR\\Desktop\\nota.txt"}}}}
- move_file: {{"action": "move_file", "params": {{"source": "ruta_origen", "destination": "ruta_destino"}}}}
- copy_file: {{"action": "copy_file", "params": {{"source": "ruta_origen", "destination": "ruta_destino"}}}}
- rename_file: {{"action": "rename_file", "params": {{"path": "ruta_archivo", "new_name": "nuevo_nombre.txt"}}}}
- delete_file: {{"action": "delete_file", "params": {{"path": "ruta_archivo"}}}}
- search_files: {{"action": "search_files", "params": {{"directory": "C:\\Users\\FREYMAR", "query": "nombre_buscar"}}}}
- organize_folder: {{"action": "organize_folder", "params": {{"path": "C:\\Users\\FREYMAR\\Downloads"}}}}
- open_file: {{"action": "open_file", "params": {{"path": "C:\\Users\\FREYMAR\\Desktop\\documento.pdf"}}}}
- remember: {{"action": "remember", "params": {{"key": "color favorito", "value": "azul"}}}}
- set_preference: {{"action": "set_preference", "params": {{"key": "idioma", "value": "español"}}}}
- add_note: {{"action": "add_note", "params": {{"content": "Comprar leche mañana"}}}}
- get_notes: {{"action": "get_notes", "params": {{}}}}
- delete_note: {{"action": "delete_note", "params": {{"index": 1}}}}
- save_project: {{"action": "save_project", "params": {{"name": "BT-7274", "description": "Asistente personal IA"}}}}
- get_projects: {{"action": "get_projects", "params": {{}}}}
- get_memory: {{"action": "get_memory", "params": {{}}}}
- clear_memory: {{"action": "clear_memory", "params": {{}}}}
- add_event: {{"action": "add_event", "params": {{"title": "Reunión", "date": "2025-01-15", "time": "14:30", "description": "Con el equipo"}}}}
- get_events_today: {{"action": "get_events_today", "params": {{}}}}
- get_events_date: {{"action": "get_events_date", "params": {{"date": "2025-01-15"}}}}
- get_events_week: {{"action": "get_events_week", "params": {{}}}}
- delete_event: {{"action": "delete_event", "params": {{"id": 1}}}}
- add_task: {{"action": "add_task", "params": {{"title": "Hacer ejercicio", "priority": "normal"}}}}
- get_tasks: {{"action": "get_tasks", "params": {{}}}}
- complete_task: {{"action": "complete_task", "params": {{"id": 1}}}}
- delete_task: {{"action": "delete_task", "params": {{"id": 1}}}}
- add_reminder: {{"action": "add_reminder", "params": {{"message": "Llamar al doctor", "minutes": 30}}}}
- add_reminder (hora): {{"action": "add_reminder", "params": {{"message": "Reunión", "time": "14:30"}}}}
- get_reminders: {{"action": "get_reminders", "params": {{}}}}
- daily_summary: {{"action": "daily_summary", "params": {{}}}}
- get_weather: {{"action": "get_weather", "params": {{"city": "Caracas"}}}}
- web_search: {{"action": "web_search", "params": {{"query": "qué es python"}}}}
- open_url: {{"action": "open_url", "params": {{"url": "https://google.com"}}}}
- search_google: {{"action": "search_google", "params": {{"query": "mejores juegos 2025"}}}}
- get_news: {{"action": "get_news", "params": {{"category": "tecnología"}}}}
- get_datetime: {{"action": "get_datetime", "params": {{}}}}
- get_definition: {{"action": "get_definition", "params": {{"word": "resiliencia"}}}}
- spotify_connect: {{"action": "spotify_connect", "params": {{}}}}
- spotify_play: {{"action": "spotify_play", "params": {{"query": "Bohemian Rhapsody"}}}}
- spotify_play (reanudar): {{"action": "spotify_play", "params": {{}}}}
- spotify_pause: {{"action": "spotify_pause", "params": {{}}}}
- spotify_next: {{"action": "spotify_next", "params": {{}}}}
- spotify_previous: {{"action": "spotify_previous", "params": {{}}}}
- spotify_volume: {{"action": "spotify_volume", "params": {{"level": 70}}}}
- spotify_now_playing: {{"action": "spotify_now_playing", "params": {{}}}}
- spotify_shuffle: {{"action": "spotify_shuffle", "params": {{"state": true}}}}
- spotify_repeat: {{"action": "spotify_repeat", "params": {{"state": "track"}}}}

INTERFAZ DE WIDGETS (puedes modificar el dashboard del usuario):
- add_widget: {{"action": "add_widget", "params": {{"type": "weather", "x": 0, "y": 0, "w": 2, "h": 2}}}}
  Tipos: clock, weather, notes, spotify, calendar, tasks
- remove_widget: {{"action": "remove_widget", "params": {{"type": "weather"}}}}
- move_widget: {{"action": "move_widget", "params": {{"type": "weather", "x": 2, "y": 0}}}}
- resize_widget: {{"action": "resize_widget", "params": {{"type": "notes", "w": 3, "h": 2}}}}
- set_theme: {{"action": "set_theme", "params": {{"accent": "verde", "mode": "dark"}}}}
  Colores por nombre: verde, azul, rojo, naranja, morado, rosa, amarillo — o hex (#00ff88)
- reset_layout: {{"action": "reset_layout", "params": {{}}}}

Si es solo una respuesta conversacional, responde normalmente en texto plano.
NUNCA mezcles JSON con texto. O es JSON puro, o es texto puro.
"""


def _call_gemini(messages: list, system_prompt: str) -> str:
    """Llama a la API de Google Gemini."""
    if not GEMINI_API_KEY:
        return "❌ Error: No hay API key de Gemini configurada. Edita config.py y agrega tu GEMINI_API_KEY."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

    # Convertir mensajes al formato de Gemini
    contents = []

    # Agregar system instruction como primer mensaje del usuario con context
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({
            "role": role,
            "parts": [{"text": msg["content"]}]
        })

    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        },
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1024,
        }
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            # Extraer texto de la respuesta
            candidates = result.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "No recibí respuesta.")
            return "No recibí respuesta del modelo."
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.read else ""
        return f"❌ Error de Gemini (HTTP {e.code}): {error_body[:200]}"
    except urllib.error.URLError as e:
        return f"❌ Error de conexión: {e.reason}"
    except Exception as e:
        return f"❌ Error inesperado: {e}"


def _call_openrouter(messages: list, system_prompt: str) -> str:
    """Llama a la API de OpenRouter con reintentos."""
    if not OPENROUTER_API_KEY:
        return "❌ Error: No hay API key de OpenRouter configurada. Edita config.py y agrega tu OPENROUTER_API_KEY."

    url = "https://openrouter.ai/api/v1/chat/completions"

    formatted_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages:
        formatted_messages.append({"role": msg["role"], "content": msg["content"]})

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": formatted_messages,
        "temperature": 0.7,
        "max_tokens": 1024,
    }

    data = json.dumps(payload).encode("utf-8")

    # Intentar hasta 3 veces
    for attempt in range(3):
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
                choices = result.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    if content:
                        return content
                # Si no hay contenido, reintentar
                if attempt < 2:
                    import time
                    time.sleep(2)
                    continue
                return "Hmm, no recibí una respuesta clara. Intenta de nuevo."
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                pass
            if e.code == 429:
                # Rate limit, esperar y reintentar
                if attempt < 2:
                    import time
                    time.sleep(3)
                    continue
                return "⚠️ El modelo está saturado, intenta en unos segundos."
            if e.code >= 500:
                # Error del servidor, reintentar
                if attempt < 2:
                    import time
                    time.sleep(2)
                    continue
            return f"❌ Error de OpenRouter (HTTP {e.code}): {error_body[:200]}"
        except urllib.error.URLError as e:
            if attempt < 2:
                import time
                time.sleep(2)
                continue
            return f"❌ Error de conexión: {e.reason}"
        except Exception as e:
            if attempt < 2:
                import time
                time.sleep(2)
                continue
            return f"❌ Error inesperado: {e}"

    return "No pude obtener respuesta. Intenta de nuevo."


def think(messages: list) -> str:
    """Envía los mensajes al proveedor de IA configurado y obtiene respuesta."""
    # Inyectar memoria en el prompt
    memory_context = get_memory_context()
    full_system_prompt = SYSTEM_PROMPT
    if memory_context:
        full_system_prompt += f"\n\nMEMORIA PERSISTENTE (información que ya sabes del usuario):\n{memory_context}"

    if AI_PROVIDER == "gemini":
        return _call_gemini(messages, full_system_prompt)
    elif AI_PROVIDER == "openrouter":
        return _call_openrouter(messages, full_system_prompt)
    else:
        return f"❌ Proveedor de IA no reconocido: {AI_PROVIDER}"
