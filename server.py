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
from agents import classify_agent
from brain import think, synthesize_answer, think_step, synthesize_plan_summary
from actions import get_system_info
from logger import log_error
from shared_memory import get_notes, get_projects, get_all_facts
from scheduler import get_tasks, get_daily_summary, restore_pending_reminders
from spotify_control import authenticate as spotify_authenticate, spotify_now_playing
from voice import speak
from voice_live import start_voice_chat, stop_voice_chat, is_voice_active
from ui_layout import get_layout, reset_layout, get_widget_data
import tools


# ═══════════════════════════════════════════
# ESTADO GLOBAL
# ═══════════════════════════════════════════

conversation = []
conversation_lock = threading.Lock()
connected_clients = set()
main_loop = None

import concurrent.futures
from security import set_confirmation_backend

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

    if action_type not in tools.TOOLS:
        return f"⚠️ Acción desconocida: {action_type}"

    try:
        result, is_ui_action = tools.execute(action_type, params)
        if is_ui_action:
            broadcast_sync({"type": "layout_update", "layout": get_layout()})
        return result
    except (TypeError, ValueError) as error:
        log_error("server", f"Parámetros inválidos para {action_type}: {error}")
        return f"⚠️ Parámetros inválidos para la acción '{action_type}'."
    except Exception as error:
        log_error("server", f"Error ejecutando {action_type}: {error}")
        return f"❌ No pude completar la acción '{action_type}'."


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


def try_parse_plan(response: str) -> list[str] | None:
    """Detecta si la IA respondió con un plan de varios pasos en vez de una acción."""
    response = response.strip()
    if response.startswith("```"):
        lines = [l for l in response.split("\n") if not l.strip().startswith("```")]
        response = "\n".join(lines).strip()
    try:
        data = json.loads(response)
        if isinstance(data, dict) and "plan" in data and isinstance(data["plan"], list):
            steps = [str(s).strip() for s in data["plan"] if str(s).strip()]
            if steps:
                return steps[:8]  # límite duro de 8 pasos por plan
    except (json.JSONDecodeError, ValueError):
        pass
    return None


MAX_PLAN_STEP_RETRIES = 1


def execute_plan(steps: list[str], user_input: str) -> str:
    """
    Ejecuta un plan de varios pasos: clasifica cada paso a un agente
    especializado, piensa -> actúa -> verifica, con un reintento simple si
    un paso falla, transmitiendo el progreso a la UI en tiempo real.
    """
    results: list[str] = []

    broadcast_sync({"type": "plan_start", "steps": steps, "total": len(steps)})

    for i, step in enumerate(steps):
        agent_name, agent_description = classify_agent(step)

        broadcast_sync({
            "type": "plan_step", "index": i, "total": len(steps),
            "description": step, "status": "running", "agent": agent_name,
        })

        step_result = None
        for attempt in range(MAX_PLAN_STEP_RETRIES + 1):
            try:
                step_response = think_step(step, results, user_input, agent_name, agent_description)
                step_action = try_parse_action(step_response)
                if step_action:
                    step_result = execute_action(step_action)
                else:
                    step_result = step_response  # el paso era razonamiento, no una acción

                if not step_result.startswith(("❌", "⚠️")):
                    break
            except Exception as e:
                step_result = f"❌ Error inesperado en el paso: {e}"

        results.append(step_result or "❌ No se pudo completar el paso.")

        broadcast_sync({
            "type": "plan_step", "index": i, "total": len(steps),
            "description": step, "status": "done", "result": results[-1],
            "agent": agent_name,
        })

    broadcast_sync({"type": "plan_end"})

    return synthesize_plan_summary(user_input, steps, results)


def _process_message_core(user_input: str) -> str:
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

    plan = try_parse_plan(response)
    if plan:
        final_response = execute_plan(plan, user_input)
        with conversation_lock:
            conversation.append({"role": "assistant", "content": final_response})
        return final_response

    action = try_parse_action(response)

    if action:
        result = execute_action(action)

        action_name = action.get("action", "")
        if action_name in tools.INFO_ACTIONS:
            final_response = synthesize_answer(user_input, result)
        else:
            final_response = result

        with conversation_lock:
            conversation.append({"role": "assistant", "content": final_response})
        return final_response
    else:
        with conversation_lock:
            conversation.append({"role": "assistant", "content": response})
        return response


def process_message(user_input: str) -> str:
    """
    Wrapper de _process_message_core que además guarda cada intercambio en
    la memoria semántica, para poder recordarlo por significado más adelante,
    sin importar cuánto tiempo pase.
    """
    response = _process_message_core(user_input)
    try:
        from semantic_memory import remember_conversation_turn
        remember_conversation_turn(user_input, response)
    except Exception:
        pass  # nunca dejar que un fallo de memoria semántica rompa la respuesta
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
