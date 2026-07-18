# -*- coding: utf-8 -*-
"""
BT-7274 - Configuración central
Carga API keys desde .env (seguro) y define constantes del proyecto.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv(Path(__file__).parent / ".env")


def _env_int(name: str, default: int, minimum: int = 1, maximum: int = 65535) -> int:
    """Lee un entero de entorno sin impedir que el asistente arranque."""
    try:
        value = int(os.getenv(name, str(default)))
        return value if minimum <= value <= maximum else default
    except (TypeError, ValueError):
        return default

# ═══════════════════════════════════════════
# MODELO DE IA
# ═══════════════════════════════════════════
AI_PROVIDER = os.getenv("AI_PROVIDER", "openrouter")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

GEMINI_MODEL = "gemini-2.0-flash"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")

# Ollama: modelos locales gratis, sin internet ni API key. Requiere la app
# de Ollama abierta y un modelo descargado (ej: `ollama pull llama3.2`).
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# ═══════════════════════════════════════════
# IDENTIDAD
# ═══════════════════════════════════════════
ASSISTANT_NAME = "BT-7274"
USER_NAME = "Piloto"

# ═══════════════════════════════════════════
# SEGURIDAD
# ═══════════════════════════════════════════

# Comandos que SIEMPRE requieren confirmación
DANGEROUS_KEYWORDS = [
    "del ", "rmdir", "format", "rm ", "shutdown", "restart",
    "taskkill", "reg delete", "diskpart", "cipher /w",
    "uninstall", "remove-item", "rd /s", "format c:",
    "net user", "net localgroup", "schtasks /delete",
    "bcdedit", "powershell -enc", "powershell -e ",
    "invoke-webrequest", "curl ", "wget ",
]

# Carpetas protegidas (no acceder sin permiso)
PROTECTED_PATHS = [
    "contraseñas", "passwords", "finanzas", "banking",
    "private", "secrets", ".ssh", ".gnupg", ".env",
    "appdata\\roaming\\mozilla", "appdata\\local\\google\\chrome\\user data",
    "credential", "wallet", "vault", "keychain",
]

# Extensiones peligrosas para ejecutar
DANGEROUS_EXTENSIONS = [".exe", ".bat", ".cmd", ".ps1", ".vbs", ".reg"]

# Máximo de archivos a eliminar sin confirmación extra
MAX_SILENT_DELETE = 0  # Siempre pedir confirmación para eliminar

# ═══════════════════════════════════════════
# APLICACIONES
# ═══════════════════════════════════════════
APPS = {
    # Navegadores
    "chrome": "start chrome",
    "google chrome": "start chrome",
    "google": "start chrome",
    "navegador": "start chrome",
    "firefox": "start firefox",
    "edge": "start msedge",
    # Office
    "word": "start \"\" \"C:\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE\"",
    "excel": "start \"\" \"C:\\Program Files\\Microsoft Office\\root\\Office16\\EXCEL.EXE\"",
    "powerpoint": "start \"\" \"C:\\Program Files\\Microsoft Office\\root\\Office16\\POWERPNT.EXE\"",
    "outlook": "start \"\" \"C:\\Program Files\\Microsoft Office\\root\\Office16\\OUTLOOK.EXE\"",
    "onenote": "start \"\" \"C:\\Program Files\\Microsoft Office\\root\\Office16\\ONENOTE.EXE\"",
    "publisher": "start \"\" \"C:\\Program Files\\Microsoft Office\\root\\Office16\\MSPUB.EXE\"",
    "access": "start \"\" \"C:\\Program Files\\Microsoft Office\\root\\Office16\\MSACCESS.EXE\"",
    # Herramientas del sistema
    "bloc de notas": "notepad",
    "notepad": "notepad",
    "explorador": "explorer",
    "calculadora": "calc",
    "paint": "mspaint",
    "terminal": "cmd",
    "configuración": "start ms-settings:",
    "recortes": "snippingtool",
    # Desarrollo
    "visual studio code": "code",
    "vscode": "code",
    "git bash": "start \"\" \"C:\\Program Files\\Git\\git-bash.exe\"",
    # Entretenimiento
    "spotify": "start spotify:",
    "steam": "start \"\" \"C:\\Users\\FREYMAR\\Documents\\Downloads\\Shindyro (juegos)\\steam\\STEAM\\Steam.exe\"",
    "discord": "start discord:",
    # Creativos
    "adobe": "start \"\" \"C:\\Program Files\\Adobe\\Adobe Creative Cloud\\ACC\\Creative Cloud.exe\"",
    "camtasia": "start \"\" \"C:\\Windows\\Installer\\{8AD50DED-EE14-4FEC-BC2C-F229C3BEFE58}\\CamtasiaIcons.exe\"",
    # Comunicación
    "whatsapp": "start whatsapp:",
    "telegram": "start telegram:",
    # Utilidades
    "winrar": "start \"\" \"C:\\Program Files\\WinRAR\\WinRAR.exe\"",
    "7zip": "start \"\" \"C:\\Users\\FREYMAR\\Desktop\\Games\\Garrys Mod - TheFenix010\\7-Zip\\7zFM.exe\"",
    "7-zip": "start \"\" \"C:\\Users\\FREYMAR\\Desktop\\Games\\Garrys Mod - TheFenix010\\7-Zip\\7zFM.exe\"",
    "utorrent": "start \"\" \"C:\\Users\\FREYMAR\\AppData\\Roaming\\uTorrent Web\\utweb.exe\"",
    "avast": "start \"\" \"C:\\Program Files\\Avast Software\\Avast\\AvastUI.exe\"",
    "ollama": "start \"\" \"C:\\Users\\FREYMAR\\AppData\\Local\\Programs\\Ollama\\ollama app.exe\"",
    # Juegos
    "roblox": "start \"\" \"C:\\Users\\FREYMAR\\AppData\\Local\\Roblox\\Versions\\version-1a951716f19e4638\\RobloxPlayerBeta.exe\"",
}

# ═══════════════════════════════════════════
# UBICACIÓN
# ═══════════════════════════════════════════
DEFAULT_CITY = os.getenv("BT7274_CITY", "Barrancabermeja").strip() or "Barrancabermeja"

# ═══════════════════════════════════════════
# SPOTIFY
# ═══════════════════════════════════════════
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"

# ═══════════════════════════════════════════
# ELEVENLABS
# ═══════════════════════════════════════════
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = "ErXwobaYiN019PkySvjV"  # Antoni

# ═══════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════
PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data"
LOG_FILE = PROJECT_DIR / "bt7274_log.txt"
HTTP_HOST = "127.0.0.1"
# 8571 en vez de 8080: el 8080 es un puerto clásico de proxy que los
# antivirus (Avast) interceptan, y cortaban la descarga de archivos grandes
# de la UI (three.min.js). Un puerto poco común no sufre esa inspección.
HTTP_PORT = _env_int("BT7274_HTTP_PORT", 8571)
WEBSOCKET_PORT = _env_int("BT7274_WEBSOCKET_PORT", 8765)
MAX_MESSAGE_CHARS = _env_int("BT7274_MAX_MESSAGE_CHARS", 10_000, minimum=100, maximum=100_000)
MAX_CONVERSATION_MESSAGES = _env_int("BT7274_MAX_CONVERSATION_MESSAGES", 12, minimum=4, maximum=50)

# Crear directorio de datos si no existe
DATA_DIR.mkdir(exist_ok=True)

# ═══════════════════════════════════════════
# VALIDACIÓN AL ARRANCAR
# ═══════════════════════════════════════════

def validate_config() -> list[str]:
    """Devuelve una lista de problemas de configuración. Vacía si todo bien."""
    problems = []

    if AI_PROVIDER == "gemini" and not GEMINI_API_KEY:
        problems.append(
            "Falta GEMINI_API_KEY en tu .env (AI_PROVIDER está en 'gemini')."
        )
    elif AI_PROVIDER == "openrouter" and not OPENROUTER_API_KEY:
        problems.append(
            "Falta OPENROUTER_API_KEY en tu .env (AI_PROVIDER está en 'openrouter')."
        )
    elif AI_PROVIDER not in ("gemini", "openrouter", "ollama"):
        problems.append(
            f"AI_PROVIDER='{AI_PROVIDER}' no es válido. Usa 'gemini', 'openrouter' u 'ollama'."
        )

    return problems
