# BT-7274 🤖

**Asistente personal de IA tipo JARVIS para Windows**

"Protocolo 3: Proteger al Piloto"

## Inicio rápido

1. Instala Python 3.11 o posterior y marca **Add Python to PATH** durante la instalación.
2. Copia `.env.example` como `.env` y configura al menos una clave de IA.
3. Instala dependencias: `py -3 -m pip install -r requirements.txt`
4. Ejecuta `py -3 server.py` o doble clic en `INICIAR_BT7274.bat`.

Las acciones que pueden modificar el sistema, archivos o datos siempre solicitan
confirmación. Es una medida deliberada para que el asistente sea potente sin
darle autorización implícita a una respuesta de IA.

## Capacidades

- 💬 Chat inteligente (OpenRouter / Gemini)
- 🎤 Chat de voz natural (Gemini Live API)
- 🎵 Control de Spotify (reproducir, pausar, siguiente, volumen)
- 🎬 Reproducir videos de YouTube
- 📂 Gestión de archivos (crear, mover, copiar, organizar)
- 🌐 Control de navegador (buscar, navegar, hacer click)
- 🖥️ Control del sistema (abrir/cerrar apps, teclado, mouse, ventanas)
- 📸 Visión de pantalla (analizar, traducir, explicar lo que ves)
- 🧠 Memoria persistente entre sesiones
- 📅 Calendario, recordatorios y tareas
- 🌤️ Clima, noticias, búsquedas web

## Estructura

```
BT-7274/
├── server.py            → Punto de entrada (abre la app)
├── brain.py             → Conexión con IA (OpenRouter)
├── voice.py             → TTS con ElevenLabs (modo texto)
├── voice_live.py        → Chat de voz Gemini Live (modo voz)
├── actions.py           → Acciones del sistema
├── file_manager.py      → Gestión de archivos
├── memory.py            → Memoria persistente
├── scheduler.py         → Calendario y tareas
├── internet.py          → Clima, noticias, búsquedas
├── spotify_control.py   → Control de Spotify
├── browser_control.py   → Control de Chrome
├── computer_control.py  → Control de mouse/teclado/ventanas
├── screen_vision.py     → Captura de pantalla para análisis
├── security.py          → Seguridad
├── logger.py            → Logging
├── cache.py             → Caché de APIs
├── config.py            → Configuración
├── .env                 → API keys (no compartir)
├── INICIAR_BT7274.bat   → Doble click para iniciar
├── ui/                  → Interfaz web
├── data/                → Datos persistentes
└── logs/                → Logs del sistema
```
