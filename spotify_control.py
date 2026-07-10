"""
BT-7274 - Control de Spotify (Premium)
Reproduce, pausa, controla volumen, busca canciones — todo sin tocar nada.
Usa la API Web de Spotify con autenticación OAuth 2.0.
"""

import json
import os
import time
import urllib.request
import urllib.error
import urllib.parse
import webbrowser
import hashlib
import base64
import secrets
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

from config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI
from logger import log_action


# Archivo donde guardamos el token
TOKEN_FILE = Path(__file__).parent / "data" / "spotify_token.json"


# ═══════════════════════════════════════════
# AUTENTICACIÓN
# ═══════════════════════════════════════════

class _CallbackHandler(BaseHTTPRequestHandler):
    """Maneja el callback de Spotify OAuth."""
    auth_code = None

    def do_GET(self):
        """Captura el código de autorización."""
        from urllib.parse import urlparse, parse_qs
        query = parse_qs(urlparse(self.path).query)

        if "code" in query:
            _CallbackHandler.auth_code = query["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
                <html><body style="font-family:Arial;text-align:center;padding-top:50px;background:#1a1a1a;color:#1DB954;">
                <h1>BT-7274 conectado a Spotify!</h1>
                <p>Ya puedes cerrar esta ventana.</p>
                </body></html>
            """)
        else:
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Error en autorizacion</h1></body></html>")

    def log_message(self, format, *args):
        """Silenciar logs del servidor HTTP."""
        pass


def _save_token(token_data: dict):
    """Guarda el token en archivo."""
    TOKEN_FILE.parent.mkdir(exist_ok=True)
    token_data["saved_at"] = time.time()
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(token_data, f, indent=2)


def _load_token() -> dict | None:
    """Carga el token desde archivo."""
    if not TOKEN_FILE.exists():
        return None
    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _token_is_valid(token_data: dict) -> bool:
    """Verifica si el token aún es válido."""
    if not token_data:
        return False
    saved_at = token_data.get("saved_at", 0)
    expires_in = token_data.get("expires_in", 3600)
    # Dar 5 min de margen
    return (time.time() - saved_at) < (expires_in - 300)


def _refresh_token(token_data: dict) -> dict | None:
    """Renueva el token usando el refresh_token."""
    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        return None

    url = "https://accounts.spotify.com/api/token"
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            new_token = json.loads(response.read().decode("utf-8"))
            # Mantener el refresh_token si no viene uno nuevo
            if "refresh_token" not in new_token:
                new_token["refresh_token"] = refresh_token
            _save_token(new_token)
            return new_token
    except Exception:
        return None


def _get_valid_token() -> str | None:
    """Obtiene un token válido, refrescándolo si es necesario."""
    token_data = _load_token()

    if not token_data:
        return None

    if _token_is_valid(token_data):
        return token_data.get("access_token")

    # Intentar refrescar
    refreshed = _refresh_token(token_data)
    if refreshed:
        return refreshed.get("access_token")

    return None


def authenticate() -> str:
    """
    Inicia el flujo de autenticación OAuth con Spotify.
    Abre el navegador para que el usuario autorice.
    """
    scopes = "user-modify-playback-state user-read-playback-state user-read-currently-playing"

    auth_url = (
        "https://accounts.spotify.com/authorize?"
        + urllib.parse.urlencode({
            "client_id": SPOTIFY_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": SPOTIFY_REDIRECT_URI,
            "scope": scopes,
        })
    )

    # Iniciar servidor local para capturar el callback
    server = HTTPServer(("127.0.0.1", 8888), _CallbackHandler)
    _CallbackHandler.auth_code = None

    # Abrir navegador
    print("  🌐 Abriendo navegador para autorizar Spotify...")
    webbrowser.open(auth_url)

    # Esperar callback (máximo 60 segundos)
    server.timeout = 60
    while _CallbackHandler.auth_code is None:
        server.handle_request()

    server.server_close()

    if not _CallbackHandler.auth_code:
        return "❌ No se recibió autorización de Spotify."

    # Intercambiar código por token
    url = "https://accounts.spotify.com/api/token"
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": _CallbackHandler.auth_code,
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "client_id": SPOTIFY_CLIENT_ID,
        "client_secret": SPOTIFY_CLIENT_SECRET,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            token_data = json.loads(response.read().decode("utf-8"))
            _save_token(token_data)
            log_action("Spotify autenticado correctamente")
            return "✅ Spotify conectado exitosamente! Ya puedo controlar tu música."
    except Exception as e:
        return f"❌ Error al obtener token de Spotify: {e}"


def _spotify_api(method: str, endpoint: str, body: dict = None) -> dict | str | None:
    """Hace una llamada a la API de Spotify."""
    token = _get_valid_token()
    if not token:
        return "NO_TOKEN"

    url = f"https://api.spotify.com/v1{endpoint}"

    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 204:
                return None  # Sin contenido (éxito)
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            # Token expirado, intentar refrescar
            token_data = _load_token()
            refreshed = _refresh_token(token_data)
            if refreshed:
                # Reintentar
                req.remove_header("Authorization")
                req.add_header("Authorization", f"Bearer {refreshed['access_token']}")
                try:
                    with urllib.request.urlopen(req, timeout=10) as response:
                        if response.status == 204:
                            return None
                        return json.loads(response.read().decode("utf-8"))
                except Exception:
                    pass
            return "NO_TOKEN"
        elif e.code == 404:
            return "NO_DEVICE"
        else:
            error_body = e.read().decode("utf-8") if e.fp else ""
            return f"ERROR:{e.code}:{error_body[:200]}"
    except Exception as e:
        return f"ERROR:0:{e}"


def _check_auth() -> str | None:
    """Verifica autenticación. Retorna mensaje de error o None si todo bien."""
    token = _get_valid_token()
    if not token:
        return ("⚠️ No estoy conectado a Spotify. Necesito que me autorices primero.\n"
                "   Escribe: 'conectar spotify' para iniciar la autorización.")
    return None


def _get_devices() -> list:
    """Obtiene la lista de dispositivos disponibles."""
    result = _spotify_api("GET", "/me/player/devices")
    if isinstance(result, dict):
        return result.get("devices", [])
    return []


def _try_activate_device_and_play(query: str = "") -> str:
    """
    Intenta activar un dispositivo de Spotify.
    Si no hay ninguno, abre la app y reintenta.
    """
    import subprocess

    # Primero, revisar si hay dispositivos disponibles
    devices = _get_devices()

    if not devices:
        # No hay dispositivos, abrir Spotify
        print("  🎵 Abriendo Spotify...")
        subprocess.Popen("spotify", shell=True)
        # Esperar a que Spotify se inicie
        for i in range(10):
            time.sleep(2)
            devices = _get_devices()
            if devices:
                break

    if not devices:
        return ("⚠️ No pude encontrar un dispositivo de Spotify activo.\n"
                "   Abre Spotify manualmente, reproduce algo por 1 segundo y vuelve a intentar.")

    # Transferir reproducción al primer dispositivo
    device_id = devices[0]["id"]
    device_name = devices[0]["name"]

    # Activar el dispositivo
    _spotify_api("PUT", "/me/player", {"device_ids": [device_id], "play": False})
    time.sleep(1)

    if not query:
        # Solo reanudar
        result = _spotify_api("PUT", "/me/player/play", None)
        if isinstance(result, str) and result.startswith("ERROR"):
            return f"❌ Error al reproducir en {device_name}: {result}"
        return f"▶️ Reproducción reanudada en {device_name}."

    # Buscar y reproducir
    search_query_raw = query
    artist_filter = ""

    separators = [" de ", " por ", " by ", " - "]
    for sep in separators:
        if sep in query.lower():
            parts = query.lower().split(sep, 1)
            search_query_raw = parts[0].strip()
            artist_filter = parts[1].strip()
            break

    if artist_filter:
        spotify_query = f"track:{search_query_raw} artist:{artist_filter}"
    else:
        spotify_query = query

    search_query = urllib.parse.quote(spotify_query)
    search_result = _spotify_api("GET", f"/search?q={search_query}&type=track&limit=5")

    if isinstance(search_result, str):
        return f"❌ Error en búsqueda: {search_result}"

    tracks = search_result.get("tracks", {}).get("items", [])
    if tracks:
        best_track = tracks[0]
        if artist_filter:
            for track in tracks:
                track_artists = " ".join([a["name"].lower() for a in track["artists"]])
                if artist_filter.lower() in track_artists:
                    if search_query_raw.lower() in track["name"].lower():
                        best_track = track
                        break
                    best_track = track

        track = best_track
        track_uri = track["uri"]
        track_name = track["name"]
        artist_name = ", ".join([a["name"] for a in track["artists"]])

        result = _spotify_api("PUT", "/me/player/play", {"uris": [track_uri]})
        if isinstance(result, str) and result.startswith("ERROR"):
            return f"❌ Error al reproducir: {result}"

        log_action(f"Spotify: reproduciendo {track_name} - {artist_name}")
        return f"🎵 Reproduciendo: {track_name} — {artist_name} (en {device_name})"

    return f"❌ No encontré '{query}' en Spotify."


# ═══════════════════════════════════════════
# CONTROL DE REPRODUCCIÓN
# ═══════════════════════════════════════════

def spotify_play(query: str = "") -> str:
    """Busca una canción/artista/playlist y la reproduce."""
    auth_error = _check_auth()
    if auth_error:
        return auth_error

    if not query:
        # Solo reanudar
        result = _spotify_api("PUT", "/me/player/play")
        if result == "NO_TOKEN":
            return "⚠️ Necesito reconectar Spotify. Escribe 'conectar spotify'."
        if result == "NO_DEVICE":
            return _try_activate_device_and_play()
        if isinstance(result, str) and result.startswith("ERROR"):
            return f"❌ Error al reproducir: {result}"
        log_action("Spotify: reanudó reproducción")
        return "▶️ Reproducción reanudada."

    # Buscar la canción/artista
    # Mejorar la búsqueda: si el usuario dice "X de Y" o "X por Y", separar track y artista
    search_query_raw = query
    artist_filter = ""

    # Detectar patrones como "canción de artista" o "canción por artista"
    separators = [" de ", " por ", " by ", " - "]
    for sep in separators:
        if sep in query.lower():
            parts = query.lower().split(sep, 1)
            search_query_raw = parts[0].strip()
            artist_filter = parts[1].strip()
            break

    # Construir query con filtros de Spotify
    if artist_filter:
        spotify_query = f"track:{search_query_raw} artist:{artist_filter}"
    else:
        spotify_query = query

    search_query = urllib.parse.quote(spotify_query)
    search_result = _spotify_api("GET", f"/search?q={search_query}&type=track&limit=5")

    if isinstance(search_result, str):
        if search_result == "NO_TOKEN":
            return "⚠️ Necesito reconectar Spotify. Escribe 'conectar spotify'."
        if search_result == "NO_DEVICE":
            return _try_activate_device_and_play(query)
        return f"❌ Error en búsqueda: {search_result}"

    # Intentar reproducir el mejor track encontrado
    tracks = search_result.get("tracks", {}).get("items", [])
    if tracks:
        # Si hay filtro de artista, buscar el mejor match
        best_track = tracks[0]
        if artist_filter:
            for track in tracks:
                track_artists = " ".join([a["name"].lower() for a in track["artists"]])
                if artist_filter.lower() in track_artists:
                    # Verificar también que el nombre del track coincida
                    if search_query_raw.lower() in track["name"].lower():
                        best_track = track
                        break
                    # Al menos el artista coincide
                    best_track = track

        track = best_track
        track_uri = track["uri"]
        track_name = track["name"]
        artist_name = ", ".join([a["name"] for a in track["artists"]])

        result = _spotify_api("PUT", "/me/player/play", {"uris": [track_uri]})
        if result == "NO_DEVICE":
            return _try_activate_device_and_play(query)
        if isinstance(result, str) and result.startswith("ERROR"):
            return f"❌ Error al reproducir: {result}"

        log_action(f"Spotify: reproduciendo {track_name} - {artist_name}")
        return f"🎵 Reproduciendo: {track_name} — {artist_name}"

    # Intentar playlist
    playlists = search_result.get("playlists", {}).get("items", [])
    if playlists:
        playlist = playlists[0]
        playlist_uri = playlist["uri"]
        playlist_name = playlist["name"]

        result = _spotify_api("PUT", "/me/player/play", {"context_uri": playlist_uri})
        if result == "NO_DEVICE":
            return _try_activate_device_and_play(query)
        if isinstance(result, str) and result.startswith("ERROR"):
            return f"❌ Error al reproducir: {result}"

        log_action(f"Spotify: reproduciendo playlist {playlist_name}")
        return f"🎵 Reproduciendo playlist: {playlist_name}"

    return f"❌ No encontré '{query}' en Spotify."


def spotify_pause() -> str:
    """Pausa la reproducción."""
    auth_error = _check_auth()
    if auth_error:
        return auth_error

    result = _spotify_api("PUT", "/me/player/pause")
    if result == "NO_DEVICE":
        return "⚠️ No hay dispositivo activo."
    if isinstance(result, str) and result.startswith("ERROR"):
        return f"❌ Error: {result}"

    log_action("Spotify: pausado")
    return "⏸️ Música pausada."


def spotify_next() -> str:
    """Siguiente canción."""
    auth_error = _check_auth()
    if auth_error:
        return auth_error

    result = _spotify_api("POST", "/me/player/next")
    if result == "NO_DEVICE":
        return "⚠️ No hay dispositivo activo."

    log_action("Spotify: siguiente canción")
    # Esperar un momento y obtener info de la nueva canción
    time.sleep(1)
    return spotify_now_playing()


def spotify_previous() -> str:
    """Canción anterior."""
    auth_error = _check_auth()
    if auth_error:
        return auth_error

    result = _spotify_api("POST", "/me/player/previous")
    if result == "NO_DEVICE":
        return "⚠️ No hay dispositivo activo."

    log_action("Spotify: canción anterior")
    time.sleep(1)
    return spotify_now_playing()


def spotify_volume(level: int) -> str:
    """Ajusta el volumen (0-100)."""
    auth_error = _check_auth()
    if auth_error:
        return auth_error

    level = max(0, min(100, level))
    result = _spotify_api("PUT", f"/me/player/volume?volume_percent={level}")
    if result == "NO_DEVICE":
        return "⚠️ No hay dispositivo activo."

    log_action(f"Spotify: volumen a {level}%")
    return f"🔊 Volumen ajustado a {level}%"


def spotify_now_playing() -> str:
    """Muestra qué está sonando ahora."""
    auth_error = _check_auth()
    if auth_error:
        return auth_error

    result = _spotify_api("GET", "/me/player/currently-playing")

    if result is None or result == "NO_DEVICE":
        return "🔇 No hay nada reproduciéndose ahora."

    if isinstance(result, str):
        if result == "NO_TOKEN":
            return "⚠️ Necesito reconectar Spotify."
        return f"❌ Error: {result}"

    if not isinstance(result, dict):
        return "🔇 No hay nada reproduciéndose."

    item = result.get("item")
    if not item:
        return "🔇 No hay nada reproduciéndose."

    track_name = item.get("name", "Desconocido")
    artists = ", ".join([a["name"] for a in item.get("artists", [])])
    album = item.get("album", {}).get("name", "")
    is_playing = result.get("is_playing", False)

    status = "▶️" if is_playing else "⏸️"
    response = f"{status} {track_name} — {artists}"
    if album:
        response += f"\n   💿 {album}"

    return response


def spotify_shuffle(state: bool = True) -> str:
    """Activa/desactiva aleatorio."""
    auth_error = _check_auth()
    if auth_error:
        return auth_error

    state_str = "true" if state else "false"
    result = _spotify_api("PUT", f"/me/player/shuffle?state={state_str}")

    if result == "NO_DEVICE":
        return "⚠️ No hay dispositivo activo."

    status = "activado" if state else "desactivado"
    log_action(f"Spotify: shuffle {status}")
    return f"🔀 Aleatorio {status}."


def spotify_repeat(state: str = "off") -> str:
    """Cambia modo de repetición. state: off, track, context."""
    auth_error = _check_auth()
    if auth_error:
        return auth_error

    if state not in ["off", "track", "context"]:
        state = "off"

    result = _spotify_api("PUT", f"/me/player/repeat?state={state}")

    if result == "NO_DEVICE":
        return "⚠️ No hay dispositivo activo."

    modes = {"off": "desactivado", "track": "repetir canción", "context": "repetir playlist"}
    log_action(f"Spotify: repetir {modes[state]}")
    return f"🔁 Repetición: {modes[state]}."
