# -*- coding: utf-8 -*-
"""
BT-7274 - Módulo de Acciones del Sistema
Abrir apps, ejecutar comandos, reproducir contenido.
"""

import subprocess
import webbrowser
import os
import urllib.request
import re
from datetime import datetime

from config import APPS
from security import request_confirmation, is_dangerous_command, sanitize_command
from logger import log_action as _log_action, log_error


def log_action(action: str):
    """Registra una acción (mantiene compatibilidad)."""
    _log_action(action)


def close_app(app_name: str) -> str:
    """Cierra una aplicación por nombre (rápido, sin output feo)."""
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
        "visual studio": "Code.exe",
        "vscode": "Code.exe",
        "teams": "ms-teams.exe",
        "whatsapp": "WhatsApp.exe",
        "telegram": "Telegram.exe",
        "firefox": "firefox.exe",
        "edge": "msedge.exe",
        "obs": "obs64.exe",
        "outlook": "OUTLOOK.EXE",
        "paint": "mspaint.exe",
    }

    app_key = app_name.lower().strip()
    process_name = close_map.get(app_key, f"{app_key}.exe")

    # taskkill se invoca sin shell; aun así rechazamos nombres que no sean un
    # ejecutable normal para impedir que el nombre se convierta en un comando.
    if not re.fullmatch(r"[A-Za-z0-9_. -]+", process_name):
        return "⚠️ El nombre de la aplicación no es válido."

    try:
        subprocess.run(
            ["taskkill", "/IM", process_name, "/F"],
            capture_output=True, text=True, timeout=5
        )
        log_action(f"Cerró aplicación: {app_name}")
        return f"✅ {app_name} cerrado."
    except Exception as e:
        return f"❌ Error al cerrar {app_name}: {e}"


def open_app(app_name: str) -> str:
    """Abre una aplicación por nombre."""
    app_key = app_name.lower().strip()

    if not app_key:
        return "⚠️ Indica qué aplicación quieres abrir."

    if app_key in APPS:
        executable = APPS[app_key]
        try:
            subprocess.Popen(executable, shell=True)
            log_action(f"Abrió aplicación: {app_name} ({executable})")
            return f"✅ Abriendo {app_name}..."
        except Exception as e:
            return f"❌ Error al abrir {app_name}: {e}"
    else:
        # Una aplicación no registrada se trata como un comando y necesita
        # aprobación explícita, igual que run_command.
        if not request_confirmation(f"Abrir aplicación o comando no registrado:\n{app_key}"):
            return "🚫 Apertura cancelada por el usuario."
        try:
            subprocess.Popen(app_key, shell=True)
            log_action(f"Abrió aplicación (directa): {app_name}")
            return f"✅ Intentando abrir {app_name}..."
        except Exception as e:
            return f"❌ No conozco la aplicación '{app_name}'. Error: {e}"


def run_command(command: str) -> str:
    """Ejecuta un comando solo tras la aprobación explícita del usuario."""
    command = (command or "").strip()
    if not command:
        return "⚠️ No recibí ningún comando para ejecutar."
    if len(command) > 2_000:
        return "⚠️ El comando es demasiado largo."

    # Si el comando encadena varios con &&, ;, etc., solo mostramos/ejecutamos
    # la primera parte — así lo que el usuario aprueba es exactamente lo que
    # se ejecuta, sin comandos extra escondidos después del primero.
    sanitized = sanitize_command(command)
    if sanitized != command:
        log_error("actions", f"run_command: comando encadenado recortado. Original: {command!r} -> {sanitized!r}")
        command = sanitized
        if not command:
            return "⚠️ No recibí ningún comando para ejecutar."

    danger_prefix = ""
    if is_dangerous_command(command):
        danger_prefix = "⚠️ COMANDO POTENCIALMENTE DESTRUCTIVO ⚠️\n\n"

    # Un comando aparentemente inocuo puede incluir redirecciones, pipes o
    # ejecutar otro programa. La IA nunca debe tener aprobación implícita.
    if not request_confirmation(f"{danger_prefix}Ejecutar comando:\n{command}"):
        return "🚫 Comando cancelado por el usuario."

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        log_action(f"Comando ejecutado: {command}")

        output = result.stdout.strip()
        error = result.stderr.strip()

        if result.returncode == 0:
            return f"✅ Ejecutado correctamente.\n{output}" if output else "✅ Ejecutado correctamente."
        else:
            return f"⚠️ Comando terminó con errores:\n{error}" if error else "⚠️ Comando terminó con código de error."
    except subprocess.TimeoutExpired:
        return "⏱️ El comando tardó demasiado y fue cancelado (límite: 30s)."
    except Exception as e:
        return f"❌ Error al ejecutar comando: {e}"


def play_youtube(query: str) -> str:
    """Busca y reproduce el primer video de YouTube directamente."""
    try:
        # Buscar en YouTube y obtener el primer resultado
        search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"

        req = urllib.request.Request(
            search_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode("utf-8", errors="replace")

        # Buscar el primer video ID en el HTML
        import re
        match = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)

        if match:
            video_id = match.group(1)
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            webbrowser.open(video_url)
            log_action(f"Reprodujo YouTube: {query} ({video_url})")
            return f"🎬 Reproduciendo '{query}' en YouTube..."
        else:
            # Fallback: abrir búsqueda
            webbrowser.open(search_url)
            log_action(f"Buscó en YouTube: {query}")
            return f"🎬 No pude encontrar el video exacto, abrí la búsqueda de '{query}'"

    except Exception:
        # Fallback si falla la red
        search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        webbrowser.open(search_url)
        log_action(f"Buscó en YouTube (fallback): {query}")
        return f"🎬 Buscando '{query}' en YouTube..."


def play_spotify_search(query: str) -> str:
    """Abre Spotify directamente con la búsqueda usando el protocolo URI."""
    # Usar el protocolo URI de Spotify que abre directo en la app
    spotify_uri = f"spotify:search:{query}"

    try:
        # Intentar abrir con el protocolo URI (abre la app directamente)
        os.startfile(spotify_uri)
        log_action(f"Abrió Spotify con búsqueda: {query}")
        return f"🎵 Abriendo '{query}' en Spotify... (dale play al primer resultado)"
    except Exception:
        # Fallback: abrir en navegador web (que redirige a la app)
        subprocess.Popen("spotify", shell=True)
        spotify_url = f"https://open.spotify.com/search/{query.replace(' ', '%20')}"
        webbrowser.open(spotify_url)
        log_action(f"Buscó en Spotify (web): {query}")
        return f"🎵 Buscando '{query}' en Spotify..."


def get_system_info() -> str:
    """Obtiene información básica del sistema (sin depender de wmic)."""
    import shutil
    import string

    info = []
    info.append(f"💻 Usuario: {os.getlogin()}")
    info.append(f"📁 Directorio actual: {os.getcwd()}")
    info.append(f"🖥️ Sistema: {os.name}")

    # Espacio en disco — usa shutil (multiplataforma, no depende de wmic)
    disk_lines = []
    if os.name == "nt":
        drives = [f"{letter}:\\" for letter in string.ascii_uppercase
                  if os.path.exists(f"{letter}:\\")]
    else:
        drives = ["/"]

    for drive in drives:
        try:
            usage = shutil.disk_usage(drive)
            free_gb = usage.free / (1024 ** 3)
            total_gb = usage.total / (1024 ** 3)
            disk_lines.append(f"   {drive} — {free_gb:.1f} GB libres de {total_gb:.1f} GB")
        except Exception:
            continue

    if disk_lines:
        info.append("💾 Discos:\n" + "\n".join(disk_lines))

    return "\n".join(info)
