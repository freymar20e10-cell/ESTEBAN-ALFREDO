# -*- coding: utf-8 -*-
"""
BT-7274 — Chat de Voz en Tiempo Real (Gemini Live API)
Conversación natural: VAD nativo, barge-in, streaming, baja latencia.
"""

import asyncio
import base64
import json
import threading
import time
import numpy as np
import sounddevice as sd

from config import GEMINI_API_KEY, ASSISTANT_NAME, USER_NAME
from logger import log_action, log_error

# ═══════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════

MODEL = "gemini-3.1-flash-live-preview"
WS_URL = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key={GEMINI_API_KEY}"

SAMPLE_RATE_IN = 16000   # Mic: 16kHz mono PCM16
SAMPLE_RATE_OUT = 24000  # Gemini output: 24kHz mono PCM16
CHUNK_MS = 100           # Enviar audio cada 100ms

SYSTEM_PROMPT = f"""Eres {ASSISTANT_NAME}, un asistente personal tipo JARVIS.
Tu piloto se llama {USER_NAME}. Eres leal, directo, eficiente y con personalidad.
Hablas en español. Eres como el Titan BT-7274 de Titanfall: protector, confiable.
Responde de forma concisa y natural. No seas demasiado largo.
Si el usuario dice "apaga bt", "desactiva voz" o "cierra el chat", responde brevemente y cierra la sesión de voz.

IMPORTANTE - ACCIONES DEL SISTEMA:
Cuando el usuario te pida hacer algo en el sistema, USA estas frases exactas:

APPS: "Abriendo Spotify" / "Cerrando Chrome"
MÚSICA: 'Reproduciendo "canción"' / "Pausando" / "Siguiente canción"
YOUTUBE: 'Reproduzco en YouTube "video"'
NAVEGADOR: 'Buscando en Google "query"' / 'Navegando a "url"' / 'Haciendo click en "texto"'
  "Bajando la página" / "Subiendo" / "Volviendo atrás" / "Cerrando pestaña"
VENTANAS: 'Enfocando "ventana"' / "Minimizando" / "Maximizando" / "Cambio de ventana"
TECLADO: 'Escribiendo "texto"' / "Presiono enter" / "Presiono escape"
  "Copiando" / "Pegando" / "Deshaciendo"

REGLA: Pon siempre los nombres/textos entre comillas para que el sistema los detecte.
Cuando el usuario pregunte sobre lo que ve en pantalla, tú recibirás la imagen automáticamente.
"""

# ═══════════════════════════════════════════
# ESTADO
# ═══════════════════════════════════════════

_is_active = False
_audio_buffer = bytearray()
_playback_active = False
_on_transcript_cb = None
_on_response_cb = None


# ═══════════════════════════════════════════
# PLAYBACK (reproduce audio de Gemini)
# ═══════════════════════════════════════════

def _playback_thread_fn():
    """Reproduce audio del buffer de salida continuamente."""
    global _playback_active, _audio_buffer

    _playback_active = True

    def callback(outdata, frames, time_info, status):
        bytes_needed = frames * 2
        if len(_audio_buffer) >= bytes_needed:
            chunk = bytes(_audio_buffer[:bytes_needed])
            del _audio_buffer[:bytes_needed]
            outdata[:] = np.frombuffer(chunk, dtype='int16').reshape(-1, 1)
        else:
            outdata[:] = np.zeros((frames, 1), dtype='int16')

    try:
        with sd.OutputStream(samplerate=SAMPLE_RATE_OUT, channels=1,
                            dtype='int16', blocksize=960, callback=callback):
            while _playback_active:
                time.sleep(0.02)
    except Exception as e:
        log_error("voice_live", f"Playback error: {e}")

    _playback_active = False


# ═══════════════════════════════════════════
# SESIÓN PRINCIPAL
# ═══════════════════════════════════════════

async def _run_session():
    """Sesión bidireccional con Gemini Live."""
    global _is_active, _audio_buffer, _playback_active

    import websockets

    _audio_buffer = bytearray()

    print("  🎤 Conectando con Gemini Live...")

    try:
        async with websockets.connect(WS_URL, max_size=None, open_timeout=10) as ws:
            # Setup
            setup = {
                "setup": {
                    "model": f"models/{MODEL}",
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "speechConfig": {
                            "voiceConfig": {
                                "prebuiltVoiceConfig": {
                                    "voiceName": "Orus"
                                }
                            }
                        }
                    },
                    "systemInstruction": {
                        "parts": [{"text": SYSTEM_PROMPT}]
                    }
                }
            }
            await ws.send(json.dumps(setup))

            resp = await asyncio.wait_for(ws.recv(), timeout=10)
            data = json.loads(resp)
            if "setupComplete" not in data:
                print(f"  ❌ Setup falló: {data}")
                _is_active = False
                return

            print(f"  ✅ Chat de voz activo. Habla naturalmente.")
            log_action("Gemini Live: sesión iniciada")

            # Iniciar playback
            pb_thread = threading.Thread(target=_playback_thread_fn, daemon=True)
            pb_thread.start()

            # Correr send y receive en paralelo
            send_task = asyncio.create_task(_send_audio(ws))
            recv_task = asyncio.create_task(_receive_audio(ws))

            while _is_active:
                await asyncio.sleep(0.1)

            send_task.cancel()
            recv_task.cancel()

    except Exception as e:
        log_error("voice_live", f"Sesión error: {e}")
        print(f"  ❌ Error: {e}")
    finally:
        _is_active = False
        _playback_active = False
        print("  🔇 Chat de voz desconectado.")


async def _send_screenshot(ws):
    """Captura la pantalla y la envía a Gemini para análisis."""
    from screen_vision import capture_screen

    print("  📸 Capturando pantalla...")
    b64_image = capture_screen(quality=50)

    if not b64_image:
        print("  ❌ No pude capturar la pantalla")
        return

    # Enviar imagen al WebSocket de Gemini Live
    msg = {
        "realtimeInput": {
            "video": {
                "data": b64_image,
                "mimeType": "image/jpeg"
            }
        }
    }

    try:
        await ws.send(json.dumps(msg))
        print("  📸 Screenshot enviado a Gemini para análisis")
    except Exception as e:
        log_error("voice_live", f"Error enviando screenshot: {e}")


async def _send_audio(ws):
    """Captura mic y envía chunks al WebSocket."""
    global _is_active, _audio_buffer

    chunk_samples = int(SAMPLE_RATE_IN * CHUNK_MS / 1000)

    try:
        stream = sd.InputStream(samplerate=SAMPLE_RATE_IN, channels=1,
                               dtype='int16', blocksize=chunk_samples)
        stream.start()

        while _is_active:
            data, _ = stream.read(chunk_samples)

            # Enviar audio
            audio_bytes = data.tobytes()
            encoded = base64.b64encode(audio_bytes).decode('utf-8')

            msg = {
                "realtimeInput": {
                    "audio": {
                        "data": encoded,
                        "mimeType": "audio/pcm;rate=16000"
                    }
                }
            }

            try:
                await ws.send(json.dumps(msg))
            except Exception:
                break

            await asyncio.sleep(CHUNK_MS / 1000 * 0.9)

        stream.stop()
        stream.close()

    except asyncio.CancelledError:
        pass
    except Exception as e:
        log_error("voice_live", f"Send error: {e}")


async def _receive_audio(ws):
    """Recibe audio y transcripciones de Gemini."""
    global _audio_buffer, _is_active

    response_text_buffer = ""  # Acumular texto de respuesta
    input_text_buffer = ""    # Acumular texto del usuario

    try:
        async for message in ws:
            if not _is_active:
                break

            resp = json.loads(message)

            if "serverContent" in resp:
                sc = resp["serverContent"]

                # Audio del modelo
                if "modelTurn" in sc and "parts" in sc["modelTurn"]:
                    # Si empieza a hablar BT, enviar lo que dijo el usuario
                    if input_text_buffer.strip():
                        if _on_transcript_cb:
                            _on_transcript_cb(input_text_buffer.strip())
                        print(f"  🗣️ {USER_NAME}: {input_text_buffer.strip()}")
                        # Check desactivar (solo si es dirigido a BT, no a una app)
                        deactivate_phrases = ["apaga bt", "desactiva", "para bt", "cierra la voz",
                                             "desactiva voz", "cierra el chat", "apaga la voz"]
                        if any(phrase in input_text_buffer.lower() for phrase in deactivate_phrases):
                            _is_active = False
                        input_text_buffer = ""

                    for part in sc["modelTurn"]["parts"]:
                        if "inlineData" in part:
                            audio_b64 = part["inlineData"]["data"]
                            _audio_buffer.extend(base64.b64decode(audio_b64))

                # Lo que dijo el usuario (acumular)
                if "inputTranscription" in sc:
                    text = sc["inputTranscription"].get("text", "")
                    if text:
                        input_text_buffer += text

                        # Detectar si pide análisis de pantalla
                        lower_input = input_text_buffer.lower()
                        screen_triggers = ["qué veo", "que veo", "qué es esto", "que es esto",
                                          "traduce esto", "traduce", "analiza mi pantalla",
                                          "analiza la pantalla", "qué dice ahí", "que dice ahi",
                                          "qué hay en pantalla", "dime qué ves", "dime que ves",
                                          "mira mi pantalla", "mira la pantalla", "lee la pantalla",
                                          "qué significa esto", "que significa esto",
                                          "cómo soluciono esto", "como soluciono esto",
                                          "ayúdame con esto", "ayudame con esto"]

                        if any(trigger in lower_input for trigger in screen_triggers):
                            # Enviar screenshot al WebSocket
                            await _send_screenshot(ws)
                            input_text_buffer = ""  # Limpiar para evitar re-trigger

                # Lo que respondió BT (acumular)
                if "outputTranscription" in sc:
                    text = sc["outputTranscription"].get("text", "")
                    if text:
                        response_text_buffer += text

                # Turno completado — enviar mensaje acumulado y ejecutar acciones
                if sc.get("turnComplete"):
                    if response_text_buffer.strip():
                        full_response = response_text_buffer.strip()
                        print(f"  🤖 {ASSISTANT_NAME}: {full_response}")
                        if _on_response_cb:
                            _on_response_cb(full_response)
                        # Detectar y ejecutar acciones del sistema
                        _execute_detected_actions(full_response)
                        response_text_buffer = ""

    except asyncio.CancelledError:
        pass
    except Exception as e:
        if _is_active:
            log_error("voice_live", f"Receive error: {e}")


# ═══════════════════════════════════════════
# DETECCIÓN Y EJECUCIÓN DE ACCIONES
# ═══════════════════════════════════════════

def _match_keywords(keywords: list, text: str) -> bool:
    """
    Busca si alguna palabra clave coincide en el texto.
    Usa regex con límites de palabra para ser flexible a variaciones.
    
    Ejemplos:
    - "reproduc" detecta: "reproduzco", "reproduciendo", "estoy reproduciendo"
    - "pausa" detecta: "pauso", "pausando", "en pausa"
    
    Args:
        keywords: lista de palabras clave para buscar
        text: texto donde buscar (se convierte a lowercase)
    
    Returns:
        True si alguna palabra clave coincide, False en caso contrario
    """
    import re
    text_lower = text.lower()
    
    for keyword in keywords:
        keyword_lower = keyword.lower()
        # Buscar con límites de palabra
        if re.search(r'\b' + re.escape(keyword_lower) + r'\b', text_lower):
            return True
        # Si no funciona, buscar como substring (más flexible)
        if keyword_lower in text_lower:
            return True
    
    return False


def _execute_detected_actions(text: str):
    """Analiza la respuesta de BT y ejecuta acciones del sistema si detecta comandos."""
    from actions import open_app, run_command, play_youtube
    from spotify_control import spotify_play, spotify_pause, spotify_next, spotify_previous
    from browser_control import (
        browser_search, browser_go_to, browser_click,
        browser_type_and_enter, browser_read_page, browser_back,
        browser_new_tab, browser_close_tab, browser_scroll
    )
    from computer_control import (
        mouse_click, mouse_scroll, type_text, press_key, hotkey,
        focus_window, minimize_window, maximize_window
    )

    text_lower = text.lower()

    # YouTube (verificar PRIMERO antes de abrir apps, para evitar conflicto con "youtube")
    if _match_keywords(["reproduzco en youtube", "busco en youtube", "reproduzco en you tube", "youtube"], text):
        import re
        match = re.search(r'[\"\"\"\'\'\`](.*?)[\"\"\"\'\'\`]', text)
        if match:
            query = match.group(1)
            if query and len(query) > 1:
                play_youtube(query)
                print(f"  ⚡ Ejecutado: youtube '{query}'")
                return
        # Fallback
        for trigger in ["youtube ", "en youtube "]:
            if trigger in text_lower:
                idx = text_lower.index(trigger) + len(trigger)
                query = text[idx:].split(".")[0].split(",")[0].strip(' "\'"')
                if query and len(query) > 2:
                    play_youtube(query)
                    print(f"  ⚡ Ejecutado: youtube '{query}'")
                    return

    # Abrir apps
    app_triggers = {
        "spotify": "spotify",
        "chrome": "chrome",
        "google": "chrome",
        "navegador": "chrome",
        "discord": "discord",
        "steam": "steam",
        "notepad": "notepad",
        "bloc de notas": "notepad",
        "explorador": "explorer",
        "calculadora": "calc",
        "visual studio": "code",
        "vscode": "code",
        "terminal": "cmd",
        "word": "winword",
        "excel": "excel",
        "powerpoint": "powerpnt",
        "teams": "msteams",
        "zoom": "zoom",
        "telegram": "telegram",
        "firefox": "firefox",
        "edge": "msedge",
        "opera": "opera",
        "brave": "brave",
        "paint": "mspaint",
        "obs": "obs64",
        "whatsapp": "explorer shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gnamwwy8!App",
        "photoshop": "photoshop",
        "davinci": "resolve",
        "camtasia": "CamtasiaStudio",
        "outlook": "outlook",
        "onenote": "onenote",
        "roblox": "explorer shell:AppsFolder\\ROBLOXCORPORATION.ROBLOX_55nm5eh3cm0pr!App",
        "utorrent": "utorrent",
        "winrar": "winrar",
        "7zip": "7zFM",
        "7-zip": "7zFM",
        "publisher": "mspub",
        "access": "msaccess",
        "ollama": "ollama",
        "kiro": "kiro",
        "reloj": "ms-clock:",
        "configuración": "ms-settings:",
        "fotos": "ms-photos:",
        "cámara": "microsoft.windows.camera:",
        "grabadora": "soundrecorder",
        "recortes": "snippingtool",
        "notas": "explorer shell:AppsFolder\\Microsoft.MicrosoftStickyNotes_8wekyb3d8bbwe!App",
        "copilot": "explorer shell:AppsFolder\\Microsoft.Copilot_8wekyb3d8bbwe!App",
        "store": "ms-windows-store:",
        "tienda": "ms-windows-store:",
        "youtube": "https://youtube.com",
    }

    if _match_keywords(["abriendo", "abrir", "abro", "lanzo", "lanzando"], text):
        for app_name, app_cmd in app_triggers.items():
            if app_name in text_lower:
                if app_cmd.startswith("http"):
                    import webbrowser
                    webbrowser.open(app_cmd)
                else:
                    open_app(app_cmd)
                print(f"  ⚡ Ejecutado: abrir {app_name}")
                return

    # Spotify - reproducir
    if _match_keywords(["reproduciendo", "reproduzco", "poniendo", "pongo"], text):
        # Extraer qué reproducir
        import re
        # Buscar entre comillas
        match = re.search(r'[""\"](.*?)[\"""]', text)
        if match:
            query = match.group(1)
            spotify_play(query)
            print(f"  ⚡ Ejecutado: spotify play '{query}'")
            return
        # Buscar después de "reproduciendo" o "poniendo"
        for trigger in ["reproduciendo ", "reproduzco ", "poniendo ", "pongo "]:
            if trigger in text_lower:
                idx = text_lower.index(trigger) + len(trigger)
                query = text[idx:].split(".")[0].split(",")[0].strip(' "\'')
                if query and len(query) > 2:
                    spotify_play(query)
                    print(f"  ⚡ Ejecutado: spotify play '{query}'")
                    return

    # Spotify - controles
    if _match_keywords(["pausando", "pauso", "pausa"], text):
        spotify_pause()
        print("  ⚡ Ejecutado: spotify pausa")
        return

    if _match_keywords(["siguiente canción", "siguiente tema", "paso la canción", "siguiente"], text):
        spotify_next()
        print("  ⚡ Ejecutado: spotify next")
        return

    if _match_keywords(["canción anterior", "tema anterior", "vuelvo a la anterior", "anterior"], text):
        spotify_previous()
        print("  ⚡ Ejecutado: spotify previous")
        return

    # Cerrar apps
    if _match_keywords(["cerrando", "cierro", "cerrar"], text):
        import subprocess
        close_map = {
            "spotify": "Spotify.exe",
            "chrome": "chrome.exe",
            "google": "chrome.exe",
            "navegador": "chrome.exe",
            "discord": "Discord.exe",
            "steam": "steam.exe",
            "word": "WINWORD.EXE",
            "excel": "EXCEL.EXE",
            "powerpoint": "POWERPNT.EXE",
            "notepad": "notepad.exe",
            "bloc de notas": "notepad.exe",
            "visual studio": "Code.exe",
            "vscode": "Code.exe",
            "explorador": "explorer.exe",
            "teams": "ms-teams.exe",
            "zoom": "Zoom.exe",
            "telegram": "Telegram.exe",
            "whatsapp": "WhatsApp.exe",
            "vlc": "vlc.exe",
            "obs": "obs64.exe",
            "firefox": "firefox.exe",
            "edge": "msedge.exe",
            "opera": "opera.exe",
            "brave": "brave.exe",
            "photoshop": "Photoshop.exe",
            "davinci": "Resolve.exe",
            "camtasia": "CamtasiaStudio.exe",
            "outlook": "OUTLOOK.EXE",
            "onenote": "ONENOTE.EXE",
            "roblox": "RobloxPlayerBeta.exe",
            "utorrent": "uTorrent.exe",
            "winrar": "WinRAR.exe",
            "7zip": "7zFM.exe",
            "7-zip": "7zFM.exe",
            "publisher": "MSPUB.EXE",
            "access": "MSACCESS.EXE",
            "ollama": "ollama.exe",
            "paint": "mspaint.exe",
            "avast": "AvastUI.exe",
            "copilot": "Microsoft.Copilot.exe",
        }

        for app_name, process_name in close_map.items():
            if app_name in text_lower:
                try:
                    subprocess.run(
                        f"taskkill /IM {process_name} /F",
                        shell=True, capture_output=True, timeout=5
                    )
                    print(f"  ⚡ Ejecutado: cerrar {app_name}")
                except Exception:
                    pass
                return

    # ═══ NAVEGADOR ═══

    # Buscar en Google
    if _match_keywords(["buscando en google", "busco en google", "búsqueda en google", "google"], text):
        import re
        match = re.search(r'[""\"](.*?)[\"""]', text)
        if match:
            browser_search(match.group(1))
            print(f"  ⚡ Ejecutado: buscar '{match.group(1)}'")
            return

    # Navegar a URL
    if _match_keywords(["navegando a", "navego a", "abriendo la página", "voy a la página", "navegando"], text):
        import re
        # Buscar URL o dominio
        match = re.search(r'(https?://\S+|www\.\S+|\w+\.\w{2,}(?:/\S*)?)', text)
        if match:
            browser_go_to(match.group(1))
            print(f"  ⚡ Ejecutado: navegar a {match.group(1)}")
            return
        # Buscar entre cualquier tipo de comillas
        match = re.search(r'[\"\"\"\'\'\`](.*?)[\"\"\"\'\'\`]', text)
        if match:
            url = match.group(1)
            if "." in url or "http" in url:
                browser_go_to(url)
                print(f"  ⚡ Ejecutado: navegar a '{url}'")
                return
            # Puede ser un nombre de sitio sin .com
            browser_go_to(url + ".com")
            print(f"  ⚡ Ejecutado: navegar a '{url}.com'")
            return

    # Click en algo
    if _match_keywords(["haciendo click", "hago click", "hago clic", "clickeando", "click"], text):
        import re
        match = re.search(r'[""\"](.*?)[\"""]', text)
        if match:
            browser_click(match.group(1))
            print(f"  ⚡ Ejecutado: click en '{match.group(1)}'")
            return

    # Scroll
    if _match_keywords(["bajando", "bajo la página", "scroll abajo"], text):
        browser_scroll("down")
        print("  ⚡ Ejecutado: scroll abajo")
        return

    if _match_keywords(["subiendo", "subo la página", "scroll arriba"], text):
        browser_scroll("up")
        print("  ⚡ Ejecutado: scroll arriba")
        return

    # Atrás
    if _match_keywords(["volviendo atrás", "vuelvo atrás", "retrocedo", "página anterior"], text):
        browser_back()
        print("  ⚡ Ejecutado: atrás")
        return

    # Nueva pestaña
    if _match_keywords(["nueva pestaña", "abro nueva pestaña", "abriendo pestaña"], text):
        import re
        match = re.search(r'[""\"](.*?)[\"""]', text)
        url = match.group(1) if match else ""
        browser_new_tab(url)
        print(f"  ⚡ Ejecutado: nueva pestaña {url}")
        return

    # Cerrar pestaña
    if _match_keywords(["cerrando pestaña", "cierro la pestaña", "cierro pestaña"], text):
        browser_close_tab()
        print("  ⚡ Ejecutado: cerrar pestaña")
        return

    # ═══ CONTROL DE VENTANAS ═══

    # Enfocar ventana
    if _match_keywords(["enfocando", "cambio a", "voy a la ventana"], text):
        import re
        match = re.search(r'[""\"](.*?)[\"""]', text)
        if match:
            focus_window(match.group(1))
            print(f"  ⚡ Ejecutado: enfocar '{match.group(1)}'")
            return

    # Minimizar
    if _match_keywords(["minimizando", "minimizo"], text):
        minimize_window()
        print("  ⚡ Ejecutado: minimizar")
        return

    # Maximizar
    if _match_keywords(["maximizando", "maximizo"], text):
        maximize_window()
        print("  ⚡ Ejecutado: maximizar")
        return

    # ═══ TECLADO ═══

    # Escribir texto
    if _match_keywords(["escribiendo", "escribo", "tecleo"], text):
        import re
        match = re.search(r'[""\"](.*?)[\"""]', text)
        if match:
            type_text(match.group(1))
            print(f"  ⚡ Ejecutado: escribir '{match.group(1)[:30]}'")
            return

    # Presionar Enter
    if _match_keywords(["presiono enter", "doy enter", "presionando enter"], text):
        press_key('enter')
        print("  ⚡ Ejecutado: enter")
        return

    # Presionar Escape
    if _match_keywords(["presiono escape", "escape", "cierro el diálogo"], text):
        press_key('escape')
        print("  ⚡ Ejecutado: escape")
        return

    # Copiar
    if _match_keywords(["copiando", "copio", "ctrl c"], text):
        hotkey('ctrl', 'c')
        print("  ⚡ Ejecutado: copiar")
        return

    # Pegar
    if _match_keywords(["pegando", "pego", "ctrl v"], text):
        hotkey('ctrl', 'v')
        print("  ⚡ Ejecutado: pegar")
        return

    # Deshacer
    if _match_keywords(["deshaciendo", "deshago", "ctrl z"], text):
        hotkey('ctrl', 'z')
        print("  ⚡ Ejecutado: deshacer")
        return

    # Alt+Tab
    if _match_keywords(["cambio de ventana", "alt tab", "siguiente ventana"], text):
        hotkey('alt', 'tab')
        print("  ⚡ Ejecutado: alt+tab")
        return

    # Alt+F4
    if _match_keywords(["alt f4", "cierro la ventana"], text):
        hotkey('alt', 'F4')
        print("  ⚡ Ejecutado: alt+f4")
        return


# ═══════════════════════════════════════════
# API PÚBLICA
# ═══════════════════════════════════════════

def start_voice_chat(on_transcript=None, on_response=None, process_fn=None) -> str:
    """Inicia el chat de voz con Gemini Live."""
    global _is_active, _on_transcript_cb, _on_response_cb

    if _is_active:
        return "🎤 El chat de voz ya está activo."

    if not GEMINI_API_KEY:
        return "❌ No hay API key de Gemini configurada."

    _is_active = True
    _on_transcript_cb = on_transcript
    _on_response_cb = on_response

    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_run_session())
        except Exception as e:
            log_error("voice_live", f"Thread error: {e}")
        finally:
            loop.close()

    threading.Thread(target=_run, daemon=True).start()
    return "🎤 Chat de voz activado. Habla naturalmente — puedes interrumpirme."


def stop_voice_chat() -> str:
    """Detiene el chat de voz."""
    global _is_active, _playback_active
    _is_active = False
    _playback_active = False
    return "🔇 Chat de voz desactivado."


def is_voice_active() -> bool:
    return _is_active
