"""
BT-7274 — Sistema de logging profesional.
Registra acciones, errores y métricas.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

from config import PROJECT_DIR

# Directorio de logs
LOG_DIR = PROJECT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Configurar logger principal
logger = logging.getLogger("BT-7274")
logger.setLevel(logging.DEBUG)

# Formato
formatter = logging.Formatter(
    "[%(asctime)s] %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Handler: archivo (todo)
file_handler = logging.FileHandler(
    LOG_DIR / "bt7274.log", encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Handler: consola (solo INFO+)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("  %(message)s")
console_handler.setFormatter(console_formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)


def log_action(action: str):
    """Registra una acción del usuario/sistema."""
    logger.info(f"ACTION | {action}")


def log_error(module: str, error: str):
    """Registra un error."""
    logger.error(f"{module} | {error}")


def log_api_call(service: str, endpoint: str, success: bool, latency_ms: int = 0):
    """Registra una llamada a API externa."""
    status = "OK" if success else "FAIL"
    logger.debug(f"API | {service} | {endpoint} | {status} | {latency_ms}ms")
