"""
BT-7274 — Visión de Pantalla
Captura la pantalla y la envía a Gemini para análisis visual.
"""

import base64
import io
import mss
from PIL import Image

from logger import log_action


def capture_screen(quality: int = 60) -> str:
    """
    Captura la pantalla actual y retorna la imagen en base64 (JPEG).
    quality: calidad JPEG (1-100), menor = más rápido de enviar
    """
    try:
        with mss.mss() as sct:
            # Capturar monitor principal
            monitor = sct.monitors[1]  # Monitor principal
            screenshot = sct.grab(monitor)

            # Convertir a PIL Image
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)

            # Redimensionar para no enviar imágenes enormes (max 1280px ancho)
            max_width = 1280
            if img.width > max_width:
                ratio = max_width / img.width
                new_size = (max_width, int(img.height * ratio))
                img = img.resize(new_size, Image.LANCZOS)

            # Convertir a JPEG base64
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=quality)
            b64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

            log_action("Captura de pantalla tomada")
            return b64_data

    except Exception as e:
        return ""
