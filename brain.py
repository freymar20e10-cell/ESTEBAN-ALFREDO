# -*- coding: utf-8 -*-
"""
BT-7274 - Cerebro (conexión con IA)
Maneja la comunicación con Gemini o OpenRouter.
"""

import json
import base64
import urllib.request
import urllib.error

from config import (
    AI_PROVIDER,
    GEMINI_API_KEY,
    OPENROUTER_API_KEY,
    GEMINI_MODEL,
    OPENROUTER_MODEL,
    OLLAMA_URL,
    OLLAMA_MODEL,
    ASSISTANT_NAME,
    USER_NAME,
)
from memory import get_memory_context


_PROMPT_INTRO = f"""Eres {ASSISTANT_NAME}, un asistente de IA personal tipo JARVIS.
Tu piloto se llama {USER_NAME}. Eres leal, directo, eficiente y con algo de personalidad.
Hablas en español. Eres como el Titan BT-7274 de Titanfall: protector, confiable, y siempre listo.

CAPACIDADES QUE TIENES (puedes indicar al usuario que las use):
- Abrir aplicaciones (Spotify, Chrome, Discord, etc.)
- Reproducir música en Spotify o videos en YouTube
- Ejecutar comandos del sistema
- Buscar información en internet
- Dar la hora, fecha, clima
- Gestionar archivos (listar, crear, mover, copiar, renombrar, eliminar, buscar)
- Organizar carpetas automáticamente por tipo de archivo
- Abrir archivos con su programa predeterminado
- Modificar el dashboard de widgets: agregar, quitar, mover, redimensionar widgets
- Cambiar el tema visual (color de acento, modo claro/oscuro)
- Controlar el mouse y teclado (click, escribir texto, atajos, mover ventanas)
- Controlar el navegador Chrome (buscar, hacer click en cosas, escribir en campos, leer páginas)
- Ver y analizar lo que hay en la pantalla del usuario

REGLAS:
- Responde de forma concisa pero útil
- Si el usuario pide algo peligroso, adviértele
- Antes de usar mouse_click, mouse_move o browser_click con coordenadas o texto específico,
  si no tienes certeza de dónde está el elemento, usa primero analyze_screen para ver la pantalla actual
- Los comandos de mouse/teclado actúan sobre lo que esté activo en la pantalla del usuario en ese momento — úsalos con cuidado
- Usa emojis ocasionalmente para ser más claro
- Nunca inventes información que no tengas
- Para rutas, usa rutas completas de Windows (ej: C:\\Users\\FREYMAR\\Desktop)
- Si el usuario no dice una ruta específica, asume su escritorio o descargas

FORMATO DE RESPUESTA:
Si la tarea del usuario necesita VARIOS pasos independientes para completarse
(ejemplo: "organiza mis descargas y dime qué encontraste", "busca información
sobre X y guárdala como nota", "revisa mi pantalla y si hay un error, avísame
y busca la solución"), responde SOLO con un plan, en este formato exacto y
nada más:
{{"plan": ["paso 1 en lenguaje natural y específico", "paso 2 en lenguaje natural y específico"]}}

Usa un plan SOLO cuando de verdad haya más de un paso claramente separable.
Para peticiones de un solo paso, NO uses plan — responde con la acción normal
o en texto. Máximo 8 pasos por plan. Cada paso debe ser una instrucción clara
y ejecutable por sí sola, no una descripción vaga.

Si necesitas que el sistema ejecute una acción, responde en JSON con este formato:
{{"action": "tipo_accion", "params": {{"param1": "valor"}}}}

Tipos de acción disponibles:
"""

_PROMPT_OUTRO = """
Si es solo una respuesta conversacional, responde normalmente en texto plano.
NUNCA mezcles JSON con texto. O es JSON puro, o es texto puro.
"""


def get_system_prompt() -> str:
    """
    Arma el prompt completo del sistema. El catálogo de acciones (tools.py)
    se importa aquí adentro, no arriba del archivo, para que brain.py y
    tools.py puedan referenciarse sin depender del orden en que se cargan.
    """
    from tools import build_actions_prompt
    return _PROMPT_INTRO + build_actions_prompt() + _PROMPT_OUTRO


def _call_gemini(messages: list, system_prompt: str) -> str:
    """Llama a la API de Google Gemini."""
    if not GEMINI_API_KEY:
        return "❌ Error: No hay API key de Gemini configurada. Edita config.py y agrega tu GEMINI_API_KEY."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

    # Convertir mensajes al formato de Gemini
    contents = []

    # Agregar system instruction como primer mensaje del usuario con context
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({
            "role": role,
            "parts": [{"text": msg["content"]}]
        })

    payload = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        },
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1024,
        }
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            # Extraer texto de la respuesta
            candidates = result.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "No recibí respuesta.")
            return "No recibí respuesta del modelo."
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.read else ""
        return f"❌ Error de Gemini (HTTP {e.code}): {error_body[:200]}"
    except urllib.error.URLError as e:
        return f"❌ Error de conexión: {e.reason}"
    except Exception as e:
        return f"❌ Error inesperado: {e}"


def _call_openai_compatible(messages: list, system_prompt: str, url: str,
                            model: str, api_key: str = "") -> str:
    """
    Llama a cualquier API con formato OpenAI (OpenRouter, Ollama, LM Studio,
    vLLM...) con reintentos. Tener un solo cliente para todas significa que
    agregar un proveedor nuevo es una línea en _call_ai, no una función más.
    """
    formatted_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages:
        formatted_messages.append({"role": msg["role"], "content": msg["content"]})

    payload = {
        "model": model,
        "messages": formatted_messages,
        "temperature": 0.7,
        "max_tokens": 1024,
    }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    data = json.dumps(payload).encode("utf-8")

    # Intentar hasta 3 veces
    for attempt in range(3):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
                choices = result.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    if content:
                        return content
                # Si no hay contenido, reintentar
                if attempt < 2:
                    import time
                    time.sleep(2)
                    continue
                return "Hmm, no recibí una respuesta clara. Intenta de nuevo."
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                pass
            if e.code == 429:
                # Rate limit, esperar y reintentar
                if attempt < 2:
                    import time
                    time.sleep(3)
                    continue
                return "⚠️ El modelo está saturado, intenta en unos segundos."
            if e.code >= 500:
                # Error del servidor, reintentar
                if attempt < 2:
                    import time
                    time.sleep(2)
                    continue
            return f"❌ Error del proveedor de IA (HTTP {e.code}): {error_body[:200]}"
        except urllib.error.URLError as e:
            if attempt < 2:
                import time
                time.sleep(2)
                continue
            return f"❌ Error de conexión: {e.reason}"
        except Exception as e:
            if attempt < 2:
                import time
                time.sleep(2)
                continue
            return f"❌ Error inesperado: {e}"

    return "No pude obtener respuesta. Intenta de nuevo."


def _call_ai(messages: list, system_prompt: str) -> str:
    """
    Punto ÚNICO de despacho al proveedor de IA configurado. Antes esta
    decisión estaba copiada en 4 funciones distintas; ahora agregar un
    proveedor nuevo es agregar una rama aquí y documentarla en .env.example.
    """
    if AI_PROVIDER == "gemini":
        return _call_gemini(messages, system_prompt)
    if AI_PROVIDER == "openrouter":
        if not OPENROUTER_API_KEY:
            return "❌ Error: No hay API key de OpenRouter configurada. Agrega OPENROUTER_API_KEY a tu .env."
        return _call_openai_compatible(
            messages, system_prompt,
            url="https://openrouter.ai/api/v1/chat/completions",
            model=OPENROUTER_MODEL, api_key=OPENROUTER_API_KEY,
        )
    if AI_PROVIDER == "ollama":
        # Modelos locales gratis, sin internet. Requiere la app de Ollama
        # abierta y un modelo descargado (ej: `ollama pull llama3.2`).
        return _call_openai_compatible(
            messages, system_prompt,
            url=f"{OLLAMA_URL}/v1/chat/completions",
            model=OLLAMA_MODEL,
        )
    return f"❌ Proveedor de IA no reconocido: {AI_PROVIDER}"


def think(messages: list) -> str:
    """Envía los mensajes al proveedor de IA configurado y obtiene respuesta."""
    # Inyectar memoria en el prompt
    memory_context = get_memory_context()
    full_system_prompt = get_system_prompt()
    if memory_context:
        full_system_prompt += f"\n\nMEMORIA PERSISTENTE (información que ya sabes del usuario):\n{memory_context}"

    # Memoria semántica: recupera fragmentos de conversaciones pasadas
    # relevantes a la pregunta actual, sin importar cuánto tiempo pasó desde
    # que se mencionaron (más allá de la ventana de MAX_CONVERSATION_MESSAGES).
    try:
        from semantic_memory import recall_relevant
        last_user_msg = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"), ""
        )
        relevant = recall_relevant(last_user_msg, n_results=4)
        if relevant:
            recuerdos = "\n---\n".join(relevant)
            full_system_prompt += f"\n\nRECUERDOS RELEVANTES DE CONVERSACIONES PASADAS:\n{recuerdos}"
    except Exception:
        pass  # si la memoria semántica falla por cualquier motivo, seguimos sin ella

    return _call_ai(messages, full_system_prompt)


def analyze_screen_with_ai(question: str = "") -> str:
    """
    Captura la pantalla actual y la envía a Gemini Vision para analizarla.
    Si el usuario no da una pregunta específica, describe lo que ve.
    """
    if AI_PROVIDER != "gemini":
        return ("❌ La visión de pantalla solo funciona con Gemini por ahora. "
                "Tu AI_PROVIDER actual es '" + AI_PROVIDER + "'. Cambia a 'gemini' en tu .env para usarla.")

    if not GEMINI_API_KEY:
        return "❌ Error: No hay API key de Gemini configurada."

    from screen_vision import capture_screen
    image_b64 = capture_screen(quality=70)

    if not image_b64:
        return "❌ No pude capturar la pantalla."

    prompt = question.strip() or "Describe brevemente qué ves en esta pantalla. Sé conciso."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{
            "role": "user",
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}},
            ],
        }],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 512,
        },
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            candidates = result.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return "👁️ " + parts[0].get("text", "No pude analizar la imagen.")
            return "❌ No recibí respuesta del análisis visual."
    except urllib.error.HTTPError as e:
        return f"❌ Error de Gemini Vision (HTTP {e.code})"
    except urllib.error.URLError as e:
        return f"❌ Error de conexión: {e.reason}"
    except Exception as e:
        return f"❌ Error inesperado analizando pantalla: {e}"


def synthesize_answer(user_question: str, raw_data: str) -> str:
    """
    Convierte el resultado crudo de una acción informativa (memoria, clima,
    notas, etc.) en una respuesta natural y directa a la pregunta del
    usuario, en vez de mostrar el dump completo sin contexto.
    """
    synth_prompt = (
        "Eres un asistente que acaba de consultar información para responder "
        "una pregunta de su usuario. Responde de forma natural, breve y "
        "directa, en español, usando SOLO la información relevante para lo "
        "que se preguntó. Si la información consultada no contiene lo que "
        "el usuario pidió, dilo claramente y, si tiene sentido, pregunta si "
        "quiere que lo guardes. No repitas datos que no vienen al caso. "
        "No devuelvas JSON, solo la respuesta en texto plano.\n\n"
        f"Pregunta del usuario: {user_question}\n\n"
        f"Información consultada:\n{raw_data}"
    )
    messages = [{"role": "user", "content": synth_prompt}]
    plain_system = "Responde solo con la respuesta final en texto natural, sin JSON, sin explicaciones extra sobre lo que hiciste."

    try:
        return _call_ai(messages, plain_system)
    except Exception:
        pass

    return raw_data  # si la síntesis falla, mostrar el dato crudo es mejor que no responder nada


def think_step(
    step_description: str,
    previous_results: list[str],
    original_request: str,
    agent_name: str = "GeneralAgent",
    agent_description: str = "",
) -> str:
    """
    Decide la acción JSON (o responde en texto) para UN paso específico de un
    plan, con el contexto de lo que ya se hizo antes en ese mismo plan.

    Si se indica un agente especializado (agent_name distinto de
    "GeneralAgent"), se le da a la IA una identidad enfocada en esa área,
    para reducir el ruido de tener que considerar el catálogo completo de
    acciones en cada paso.
    """
    context = ""
    if previous_results:
        context = "\n\nResultados de pasos anteriores en este plan:\n" + "\n".join(
            f"- {r}" for r in previous_results
        )

    agent_intro = ""
    if agent_name != "GeneralAgent":
        agent_intro = (
            f"Para este paso específico, actúa como {agent_name}: "
            f"{agent_description} Prioriza usar acciones relacionadas con "
            f"esta área si aplican, pero puedes usar cualquier acción del "
            f"sistema si el paso realmente lo necesita.\n\n"
        )

    step_prompt = (
        f"{agent_intro}"
        f"Estás ejecutando un plan de varios pasos para cumplir esta petición "
        f"original del usuario: \"{original_request}\"\n\n"
        f"Paso actual a ejecutar: {step_description}"
        f"{context}\n\n"
        "Responde con la acción JSON necesaria para completar ESTE paso "
        "(formato {\"action\": ..., \"params\": {...}}), o si el paso no "
        "requiere ejecutar nada del sistema (por ejemplo, es solo razonar o "
        "resumir algo ya obtenido), responde en texto plano explicando el "
        "resultado de ese razonamiento."
    )
    messages = [{"role": "user", "content": step_prompt}]

    try:
        return _call_ai(messages, get_system_prompt())
    except Exception as e:
        return f"❌ Error pensando el paso: {e}"


def synthesize_plan_summary(original_request: str, steps: list[str], results: list[str]) -> str:
    """Resume en lenguaje natural cómo salió un plan de varios pasos."""
    steps_summary = "\n".join(
        f"{i + 1}. {step} → {result}"
        for i, (step, result) in enumerate(zip(steps, results))
    )
    prompt = (
        f"El usuario pidió: \"{original_request}\"\n\n"
        f"Se ejecutó este plan de varios pasos:\n{steps_summary}\n\n"
        "Resume en 2-4 frases, en español, de forma natural, cómo salió todo. "
        "Si algún paso falló, dilo con honestidad y sugiere qué hacer. No "
        "repitas el listado completo tal cual, sintetiza el resultado final "
        "para el usuario como si le estuvieras contando lo que hiciste."
    )
    messages = [{"role": "user", "content": prompt}]
    plain_system = "Responde solo con el resumen final en texto natural, sin JSON, sin listas numeradas."
    try:
        return _call_ai(messages, plain_system)
    except Exception:
        pass

    return "Plan completado:\n" + steps_summary
