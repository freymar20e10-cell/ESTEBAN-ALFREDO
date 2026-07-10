"""
BT-7274 - Módulo de Voz
Entrada: Micrófono con Google Speech Recognition (gratis)
Salida: Windows SAPI (gratis) o ElevenLabs (opcional, de pago)
"""

import io
import json
import wave
import tempfile
import threading
import urllib.request
import urllib.error
import urllib.parse
import os
import time

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as wav_write, read as wav_read

from config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID
from logger import log_action


# ═══════════════════════════════════════════
# ENTRADA DE VOZ — Ahora manejada por voice_live.py (Gemini Live)
# Este módulo solo se usa para speak() (ElevenLabs TTS en modo texto)
# ═══════════════════════════════════════════

# Parámetros de grabación (usados por voice_live.py como fallback)
SAMPLE_RATE = 16000
CHANNELS = 1


def _google_speech_recognize(wav_bytes: bytes) -> str:
    """
    Reconoce voz usando la librería SpeechRecognition con Google.
    """
    import speech_recognition as sr
    import tempfile
    import os

    temp_wav = os.path.join(tempfile.gettempdir(), "bt7274_input.wav")
    with open(temp_wav, "wb") as f:
        f.write(wav_bytes)

    recognizer = sr.Recognizer()

    try:
        with sr.AudioFile(temp_wav) as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio, language="es-ES")
        return text
    except Exception:
        return ""


# ═══════════════════════════════════════════
# SALIDA DE VOZ (Texto → Audio)
# Prioridad: Windows SAPI (gratis) → ElevenLabs (si hay API key)
# ═══════════════════════════════════════════

def speak(text: str):
    """Convierte texto a voz. Usa Windows SAPI por defecto (gratis)."""
    clean_text = _clean_for_speech(text)
    if not clean_text.strip():
        return

    if len(clean_text) > 400:
        clean_text = clean_text[:400] + "..."

    # ElevenLabs solo si está explícitamente habilitado
    use_elevenlabs = os.getenv("TTS_PROVIDER", "windows").lower() == "elevenlabs"
    if use_elevenlabs and ELEVENLABS_API_KEY:
        try:
            _elevenlabs_stream_and_play(clean_text)
            return
        except Exception:
            pass

    _windows_speak(clean_text)


def _windows_speak(text: str):
    """TTS gratuito usando voces nativas de Windows (SAPI)."""
    import subprocess

    safe = text.replace("'", "''").replace('"', ' ')
    ps_cmd = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$s.Rate = 0; "
        f"$s.Speak('{safe}')"
    )
    try:
        flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            creationflags=flags,
            timeout=120,
            capture_output=True,
        )
        log_action("TTS Windows SAPI")
    except Exception:
        pass


def _elevenlabs_stream_and_play(text: str):
    """Genera audio con ElevenLabs en streaming y reproduce mientras descarga."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/stream"

    payload = {
        "text": text,
        "model_id": "eleven_flash_v2_5",
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.75,
            "style": 0.2,
            "use_speaker_boost": True,
        }
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("xi-api-key", ELEVENLABS_API_KEY)
    req.add_header("Accept", "audio/mpeg")

    try:
        import pygame

        # Descargar el audio en streaming
        with urllib.request.urlopen(req, timeout=15) as response:
            audio_data = response.read()

        if not audio_data:
            return

        # Guardar y reproducir
        temp_file = os.path.join(tempfile.gettempdir(), "bt7274_voice.mp3")
        with open(temp_file, "wb") as f:
            f.write(audio_data)

        # Reiniciar mixer y reproducir
        try:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except Exception:
            pass

        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            time.sleep(0.03)

        pygame.mixer.music.unload()
        pygame.mixer.quit()

    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("  ❌ API key de ElevenLabs inválida.")
        elif e.code == 429:
            print("  ⚠️ Límite de ElevenLabs alcanzado.")
    except Exception:
        pass


def _clean_for_speech(text: str) -> str:
    """Limpia texto para TTS — quita emojis y símbolos raros."""
    import re
    # Quitar emojis
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u2640-\u2642"
        "\u2600-\u2B55"
        "\u200d"
        "\u23cf"
        "\u23e9"
        "\u231a"
        "\ufe0f"
        "\u3030"
        "═╔╗╚╝╠╣║"
        "]+",
        flags=re.UNICODE
    )
    text = emoji_pattern.sub("", text)
    # Quitar múltiples espacios
    text = re.sub(r'\s+', ' ', text).strip()
    return text


