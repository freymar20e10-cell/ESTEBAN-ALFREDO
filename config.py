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

# ═══════════════════════════════════════════
# MODELO DE IA
# ═══════════════════════════════════════════
AI_PROVIDER = os.getenv("AI_PROVIDER", "openrouter")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

GEMINI_MODEL = "gemini-2.0-flash"
OPENROUTER_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"

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
DEFAULT_CITY = "Barrancabermeja"

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

# Crear directorio de datos si no existe
DATA_DIR.mkdir(exist_ok=True)
