# -*- coding: utf-8 -*-
"""
BT-7274 — Servidor Unificado
Una sola app: interfaz gráfica + chat de voz en tiempo real.
Ejecutar: python server.py
"""

import asyncio
import json
import sys
import threading
import webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import websockets

# Función para printear sin errores de encoding
def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        # Si hay error, reemplazar emojis y reintentar
        text = text.replace('🌐', '[*]').replace('✅', '[OK]').replace('❌', '[X]').replace('🫡', '^_^')
        print(text)

sys.path.insert(0, str(Path(__file__).parent))

from config import (
    ASSISTANT_NAME, USER_NAME, HTTP_HOST, HTTP_PORT,
    WEBSOCKET_PORT, MAX_MESSAGE_CHARS, MAX_CONVERSATION_MESSAGES,
)
from brain import think, analyze_screen_with_ai
from actions import open_app, close_app, run_command, play_youtube, play_spotify_search, get_system_info, log_action
from logger import log_error
from file_manager import (
    list_files, create_folder, create_file, read_file,
    move_file, copy_file, rename_file, delete_file,
    search_files, organize_folder, open_file
)
from shared_memory import (
    remember, set_preference, add_note, get_notes,
    delete_note, save_project, get_projects, get_all_facts, clear_memory
)
from scheduler import (
    add_event, get_events_today, get_events_by_date, get_events_week,
    delete_event, add_task, get_tasks, complete_task, delete_task,
    add_reminder, get_reminders, get_daily_summary, restore_pending_reminders
)
from internet import get_weather, web_search, open_url, search_and_open, get_news, get_datetime, get_definition
from spotify_control import (
    authenticate as spotify_authenticate, spotify_play, spotify_pause,
    spotify_next, spotify_previous, spotify_volume, spotify_now_playing,
    spotify_shuffle, spotify_repeat
)
from voice import speak
from voice_live import start_voice_chat, stop_voice_chat, is_voice_active
from computer_control import (
    mouse_click, mouse_double_click, mouse_right_click, mouse_move, mouse_scroll,
    type_text, press_key, hotkey,
    focus_window, minimize_window, maximize_window, list_windows,
    copy_selection, paste_text, select_all, undo,
)
from browser_control import (
    browser_search, browser_go_to, browser_click, browser_type,
    browser_type_and_enter, browser_read_page, browser_back,
    browser_new_tab, browser_close_tab, browser_scroll, close_browser,
)
from ui_layout import (
    get_layout, add_widget, remove_widget, move_widget,
    resize_widget, set_theme, reset_layout, get_widget_data,
)


# ═══════════════════════════════════════════
# ESTADO GLOBAL
# ═══════════════════════════════════════════

conversation = []
conversation_lock = threading.Lock()
connected_clients = set()
main_loop = None

import concurrent.futures
from security import request_confirmation, set_confirmation_backend

# Confirmaciones pendientes: id -> Future que se resuelve cuando el usuario responde en la UI
_pending_confirmations: dict[str, concurrent.futures.Future] = {}
_confirmation_counter = 0
_confirmation_lock = threading.Lock()


def _ask_confirmation_via_ui(description: str) -> bool:
    """Se ejecuta en el hilo del executor (bloqueante ahí, no en el loop principal).
    Manda la pregunta a TODOS los clientes conectados y espera hasta 60s la respuesta."""
    global _confirmation_counter
    if not connected_clients or main_loop is None:
        return False  # Sin UI conectada, no hay forma segura de confirmar

    with _confirmation_lock:
        _confirmation_counter += 1
        confirm_id = f"confirm-{_confirmation_counter}"

    future = concurrent.futures.Future()
    _pending_confirmations[confirm_id] = future

    broadcast_sync({
        "type": "confirmation_request",
        "id": confirm_id,
        "description": description,
    })

    try:
        return future.result(timeout=60)  # Espera hasta 60s la respuesta del usuario
    except concurrent.futures.TimeoutError:
        return False
    finally:
        _pending_confirmations.pop(confirm_id, None)


set_confirmation_backend(_ask_confirmation_via_ui)


# ═══════════════════════════════════════════
# ACCIONES
# ═══════════════════════════════════════════

def execute_action(action_data: dict) -> str:
    if not isinstance(action_data, dict):
        return "⚠️ La acción recibida no tiene un formato válido."
    action_type = action_data.get("action", "")
    params = action_data.get("params", {})
    if not isinstance(action_type, str) or not action_type.strip():
        return "⚠️ La acción no tiene un nombre válido."
    if not isinstance(params, dict):
        return "⚠️ Los parámetros de la acción no son válidos."

    actions_map = {
        "open_app": lambda: open_app(params.get("name", "")),
        "close_app": lambda: close_app(params.get("name", "")),
        "run_command": lambda: run_command(params.get("command", "")),
        "play_youtube": lambda: play_youtube(params.get("query", "")),
        "play_spotify": lambda: play_spotify_search(params.get("query", "")),
        "system_info": lambda: get_system_info(),
        "list_files": lambda: list_files(params.get("path", ".")),
        "create_folder": lambda: create_folder(params.get("path", "")),
        "create_file": lambda: create_file(params.get("path", ""), params.get("content", "")),
        "read_file": lambda: read_file(params.get("path", "")),
        "move_file": lambda: move_file(params.get("source", ""), params.get("destination", "")),
        "copy_file": lambda: copy_file(params.get("source", ""), params.get("destination", "")),
        "rename_file": lambda: rename_file(params.get("path", ""), params.get("new_name", "")),
        "delete_file": lambda: delete_file(params.get("path", "")),
        "search_files": lambda: search_files(params.get("directory", "."), params.get("query", "")),
        "organize_folder": lambda: organize_folder(params.get("path", "")),
        "open_file": lambda: open_file(params.get("path", "")),
        "remember": lambda: remember(params.get("key", ""), params.get("value", "")),
        "set_preference": lambda: set_preference(params.get("key", ""), params.get("value", "")),
        "add_note": lambda: add_note(params.get("content", "")),
        "get_notes": lambda: get_notes(),
        "delete_note": lambda: delete_note(int(params.get("index", 0))),
        "save_project": lambda: save_project(params.get("name", ""), params.get("description", "")),
        "get_projects": lambda: get_projects(),
        "get_memory": lambda: get_all_facts(),
        "clear_memory": lambda: clear_memory(),
        "add_event": lambda: add_event(params.get("title", ""), params.get("date", ""), params.get("time", ""), params.get("description", "")),
        "get_events_today": lambda: get_events_today(),
        "get_events_date": lambda: get_events_by_date(params.get("date", "")),
        "get_events_week": lambda: get_events_week(),
        "delete_event": lambda: delete_event(int(params.get("id", 0))),
        "add_task": lambda: add_task(params.get("title", ""), params.get("priority", "normal")),
        "get_tasks": lambda: get_tasks(params.get("show_completed", False)),
        "complete_task": lambda: complete_task(int(params.get("id", 0))),
        "delete_task": lambda: delete_task(int(params.get("id", 0))),
        "add_reminder": lambda: add_reminder(params.get("message", ""), int(params.get("minutes", 0)), params.get("time", "")),
        "get_reminders": lambda: get_reminders(),
        "daily_summary": lambda: get_daily_summary(),
        "get_weather": lambda: get_weather(params.get("city", "")),
        "web_search": lambda: web_search(params.get("query", "")),
        "open_url": lambda: open_url(params.get("url", "")),
        "search_google": lambda: search_and_open(params.get("query", "")),
        "get_news": lambda: get_news(params.get("category", "general")),
        "get_datetime": lambda: get_datetime(),
        "get_definition": lambda: get_definition(params.get("word", "")),
        "spotify_connect": lambda: spotify_authenticate(),
        "spotify_play": lambda: spotify_play(params.get("query", "")),
        "spotify_pause": lambda: spotify_pause(),
        "spotify_next": lambda: spotify_next(),
        "spotify_previous": lambda: spotify_previous(),
        "spotify_volume": lambda: spotify_volume(int(params.get("level", 50))),
        "spotify_now_playing": lambda: spotify_now_playing(),
        "spotify_shuffle": lambda: spotify_shuffle(params.get("state", True)),
        "spotify_repeat": lambda: spotify_repeat(params.get("state", "off")),
        # Control de mouse/teclado/ventanas
        "mouse_click": lambda: mouse_click(int(params.get("x", 0)), int(params.get("y", 0))),
        "mouse_double_click": lambda: mouse_double_click(int(params.get("x", 0)), int(params.get("y", 0))),
        "mouse_right_click": lambda: mouse_right_click(int(params.get("x", 0)), int(params.get("y", 0))),
        "mouse_move": lambda: mouse_move(int(params.get("x", 0)), int(params.get("y", 0))),
        "mouse_scroll": lambda: mouse_scroll(int(params.get("clicks", -3))),
        "type_text": lambda: type_text(params.get("text", "")),
        "press_key": lambda: press_key(params.get("key", "")),
        "hotkey": lambda: hotkey(*params.get("keys", [])),
        "focus_window": lambda: focus_window(params.get("title", "")),
        "minimize_window": lambda: minimize_window(params.get("title", "")),
        "maximize_window": lambda: maximize_window(params.get("title", "")),
        "list_windows": lambda: list_windows(),
        "copy_selection": lambda: copy_selection(),
        "paste_text": lambda: paste_text(),
        "select_all": lambda: select_all(),
        "undo": lambda: undo(),
        # Control de navegador (Selenium)
        "browser_search": lambda: browser_search(params.get("query", "")),
        "browser_go_to": lambda: browser_go_to(params.get("url", "")),
        "browser_click": lambda: browser_click(params.get("text", "")),
        "browser_type": lambda: browser_type(params.get("text", ""), params.get("field_hint", "")),
        "browser_type_and_enter": lambda: browser_type_and_enter(params.get("text", "")),
        "browser_read_page": lambda: browser_read_page(),
        "browser_back": lambda: browser_back(),
        "browser_new_tab": lambda: browser_new_tab(params.get("url", "")),
        "browser_close_tab": lambda: browser_close_tab(),
        "browser_scroll": lambda: browser_scroll(params.get("direction", "down")),
        "close_browser": lambda: close_browser(),
        # Visión de pantalla
        "analyze_screen": lambda: analyze_screen_with_ai(params.get("question", "")),
        # UI / Widgets
        "add_widget": lambda: add_widget(
            params.get("type", params.get("widget", "")),
            int(params.get("x", 0)),
            int(params.get("y", 0)),
            int(params.get("w", 2)),
            int(params.get("h", 2)),
        ),
        "remove_widget": lambda: remove_widget(
            params.get("id", params.get("widget_id", "")),
            params.get("type", params.get("widget", "")),
        ),
        "move_widget": lambda: move_widget(
            params.get("id", params.get("widget_id", "")),
            params.get("type", params.get("widget", "")),
            int(params.get("x", 0)),
            int(params.get("y", 0)),
        ),
        "resize_widget": lambda: resize_widget(
            params.get("id", params.get("widget_id", "")),
            params.get("type", params.get("widget", "")),
            int(params.get("w", 2)),
            int(params.get("h", 2)),
        ),
        "set_theme": lambda: set_theme(
            params.get("accent", params.get("color", "")),
            params.get("mode", ""),
        ),
        "reset_layout": lambda: reset_layout(),
    }

    UI_ACTIONS = {
        "add_widget", "remove_widget", "move_widget",
        "resize_widget", "set_theme", "reset_layout",
    }

    # Estas acciones borran información o producen una interacción que no se
    # puede deshacer con fiabilidad. La IA puede proponerlas, pero no aprobarlas.
    confirmation_required = {
        "delete_note": "Eliminar una nota guardada",
        "delete_event": "Eliminar un evento del calendario",
        "delete_task": "Eliminar una tarea",
        "clear_memory": "Borrar toda la memoria del asistente",
        "close_browser": "Cerrar el navegador controlado",
    }
    if action_type in confirmation_required:
        if not request_confirmation(confirmation_required[action_type]):
            return "🚫 Acción cancelada por el usuario."

    if action_type in actions_map:
        try:
            result = actions_map[action_type]()
            if action_type in UI_ACTIONS:
                broadcast_sync({"type": "layout_update", "layout": get_layout()})
            return result
        except (TypeError, ValueError) as error:
            log_error("server", f"Parámetros inválidos para {action_type}: {error}")
            return f"⚠️ Parámetros inválidos para la acción '{action_type}'."
        except Exception as error:
            log_error("server", f"Error ejecutando {action_type}: {error}")
            return f"❌ No pude completar la acción '{action_type}'."
    return f"⚠️ Acción desconocida: {action_type}"


def try_parse_action(response: str) -> dict | None:
    response = response.strip()
    if response.startswith("```"):
        lines = response.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        response = "\n".join(lines).strip()
    try:
        data = json.loads(response)
        if isinstance(data, dict) and "action" in data:
            return data
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def _ui_action(fn):
    """Ejecuta acción de UI y emite broadcast del layout."""
    result = fn()
    broadcast_sync({"type": "layout_update", "layout": get_layout()})
    return result


def process_message(user_input: str) -> str:
    global conversation

    direct = {
        "estado": get_system_info,
        "memoria": get_all_facts,
        "notas": get_notes,
        "proyectos": get_projects,
        "agenda": get_daily_summary,
        "tareas": get_tasks,
        "conectar spotify": spotify_authenticate,
        "qué suena": spotify_now_playing,
        "que suena": spotify_now_playing,
        "restablece el dashboard": lambda: _ui_action(reset_layout),
        "restablecer dashboard": lambda: _ui_action(reset_layout),
    }

    if user_input.lower().strip() in direct:
        return direct[user_input.lower().strip()]()

    with conversation_lock:
        conversation.append({"role": "user", "content": user_input})
        if len(conversation) > MAX_CONVERSATION_MESSAGES:
            conversation = conversation[-MAX_CONVERSATION_MESSAGES:]
        snapshot = list(conversation)

    response = think(snapshot)
    action = try_parse_action(response)

    if action:
        result = execute_action(action)
        with conversation_lock:
            conversation.append({"role": "assistant", "content": result})
        return result
    else:
        with conversation_lock:
            conversation.append({"role": "assistant", "content": response})
        return response


# ═══════════════════════════════════════════
# CHAT DE VOZ (Gemini Live API - tiempo real)
# ═══════════════════════════════════════════

def _on_voice_transcript(text):
    """Callback cuando el usuario habla (transcripción)."""
    broadcast_sync({"type": "voice_detected", "content": text})

def _on_voice_response(text):
    """Callback cuando BT responde (transcripción de la respuesta)."""
    broadcast_sync({"type": "response", "content": text})


def broadcast_sync(data: dict):
    """Envía mensaje a todos los clientes conectados."""
    message = json.dumps(data)
    for client in list(connected_clients):
        try:
            asyncio.run_coroutine_threadsafe(client.send(message), main_loop)
        except Exception:
            pass


# ═══════════════════════════════════════════
# WEBSOCKET HANDLER
# ═══════════════════════════════════════════

async def handle_client(websocket):
    connected_clients.add(websocket)
    print(f"  [+] Cliente conectado")

    # Enviar layout actual al conectar
    try:
        await websocket.send(json.dumps({
            "type": "layout_update",
            "layout": get_layout(),
        }))
    except Exception:
        pass

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
            except (json.JSONDecodeError, TypeError):
                await websocket.send(json.dumps({"type": "error", "content": "Mensaje inválido."}))
                continue
            if not isinstance(data, dict):
                await websocket.send(json.dumps({"type": "error", "content": "Mensaje inválido."}))
                continue
            msg_type = data.get("type", "")
            content = data.get("content", "")

            if msg_type == "get_layout":
                await websocket.send(json.dumps({
                    "type": "layout_update",
                    "layout": get_layout(),
                }))
                continue

            if msg_type == "widget_data":
                widget_type = data.get("widget", "")
                # Clima y Spotify pueden consultar red; no bloquean el loop
                # WebSocket ni las confirmaciones de otras acciones.
                payload = await asyncio.to_thread(get_widget_data, widget_type)
                await websocket.send(json.dumps({
                    "type": "widget_data",
                    "widget": widget_type,
                    "data": payload,
                }))
                continue

            if msg_type == "confirmation_response":
                confirm_id = data.get("id", "")
                approved = bool(data.get("approved", False))
                future = _pending_confirmations.get(confirm_id)
                if future and not future.done():
                    future.set_result(approved)
                continue

            if msg_type == "message":
                if not isinstance(content, str) or not content.strip():
                    await websocket.send(json.dumps({"type": "error", "content": "Escribe un mensaje válido."}))
                    continue
                if len(content) > MAX_MESSAGE_CHARS:
                    await websocket.send(json.dumps({"type": "error", "content": "El mensaje es demasiado largo."}))
                    continue
                # Verificar si es comando de voz
                content_lower = content.lower().strip()

                # Detectar intención de activar chat de voz (flexible)
                activate_keywords = ["activa chat de voz", "activar chat de voz", "chat de voz",
                                    "activa voz", "activar voz", "activa el chat de voz",
                                    "activar el chat de voz", "prende el micro", "prende micro",
                                    "enciende el micro", "activa micro", "activa micrófono",
                                    "activa microfono", "modo voz", "hablar"]
                
                deactivate_keywords = ["desactiva chat de voz", "desactivar chat de voz",
                                      "desactiva voz", "desactivar voz", "apaga voz",
                                      "apaga el micro", "desactiva micro", "apaga micro",
                                      "desactiva micrófono", "desactiva microfono", "para voz"]

                is_activate = any(kw in content_lower for kw in activate_keywords)
                is_deactivate = any(kw in content_lower for kw in deactivate_keywords)

                if is_activate and not is_voice_active():
                    result = start_voice_chat(_on_voice_transcript, _on_voice_response, process_message)
                    await websocket.send(json.dumps({"type": "response", "content": result}))
                    await websocket.send(json.dumps({
                        "type": "status", "state": "listening", "text": "🎤 CHAT DE VOZ ACTIVO"
                    }))
                    continue

                if is_activate and is_voice_active():
                    await websocket.send(json.dumps({
                        "type": "response",
                        "content": "🎤 El chat de voz ya está activo. Habla naturalmente."
                    }))
                    continue

                if is_deactivate:
                    result = stop_voice_chat()
                    await websocket.send(json.dumps({"type": "response", "content": result}))
                    await websocket.send(json.dumps({
                        "type": "status", "state": "listening", "text": "● EN LÍNEA"
                    }))
                    continue

                # Mensaje normal de texto
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, process_message, content)

                # Hablar y enviar texto AL MISMO TIEMPO
                speak_thread = threading.Thread(target=speak, args=(response,), daemon=True)
                speak_thread.start()

                await websocket.send(json.dumps({
                    "type": "response",
                    "content": response
                }))

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.discard(websocket)


# ═══════════════════════════════════════════
# HTTP SERVER
# ═══════════════════════════════════════════

class BTHTTPRequestHandler(SimpleHTTPRequestHandler):
    """Sirve la UI estática y expone API JSON para widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent / "ui"), **kwargs)

    def log_message(self, format, *args):
        return

    def _send_json(self, payload: dict, status: int = 200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/layout":
            self._send_json(get_layout())
            return
        if self.path.startswith("/api/widget/"):
            widget_type = self.path.split("/api/widget/", 1)[1].split("?", 1)[0]
            self._send_json(get_widget_data(widget_type))
            return
        return super().do_GET()


def start_http_server():
    httpd = ThreadingHTTPServer((HTTP_HOST, HTTP_PORT), BTHTTPRequestHandler)
    httpd.serve_forever()


# ═══════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════

async def main():
    global main_loop
    main_loop = asyncio.get_event_loop()
    restored_reminders = restore_pending_reminders()

    from config import validate_config
    problems = validate_config()
    if problems:
        print("\n  ⚠️  PROBLEMAS DE CONFIGURACIÓN DETECTADOS:\n")
        for p in problems:
            print(f"     - {p}")
        print("\n  Corrige tu archivo .env antes de continuar.\n")
        print("  El servidor seguirá abierto, pero el chat con IA no funcionará")
        print("  hasta que arregles esto.\n")

    print(f"""
================================================================================
                    BT-7274 - ASISTENTE PERSONAL
                 "Protocolo 3: Proteger al Piloto"
================================================================================

  Web UI:      http://{HTTP_HOST}:{HTTP_PORT}
  Chat texto:  Siempre disponible
  Chat voz:    Escribe 'activa chat de voz'
  
  Para cerrar: Ctrl+C
================================================================================
""")
    if restored_reminders:
        print(f"  [OK] {restored_reminders} recordatorio(s) restaurado(s).")

    # HTTP server
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()

    # Abrir navegador
    print("  [>] Abriendo BT-7274...")
    webbrowser.open(f"http://{HTTP_HOST}:{HTTP_PORT}")
    print(f"  [OK] Listo. Escribe o activa chat de voz.\n")

    # Beep
    try:
        import winsound
        winsound.Beep(600, 100)
        winsound.Beep(800, 100)
        winsound.Beep(1000, 150)
    except Exception:
        pass

    # WebSocket
    async with websockets.serve(
        handle_client, HTTP_HOST, WEBSOCKET_PORT,
        ping_interval=20, ping_timeout=20, max_size=MAX_MESSAGE_CHARS * 2,
    ):
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n  BT-7274: Sistemas apagados. Hasta luego, {USER_NAME}.")
