# -*- coding: utf-8 -*-
"""
BT-7274 - Registro de Agentes Especializados

No son procesos separados ni llamadas de IA independientes (sería caro y
lento para un asistente personal de un solo usuario). Son identidades con
un área de responsabilidad clara, que el Planner usa para darle a cada paso
de un plan un enfoque específico, en vez de mezclar el catálogo completo de
acciones del sistema en cada decisión.
"""

AGENT_REGISTRY = {
    "ResearchAgent": {
        "description": "Investiga información: búsquedas web, noticias, definiciones, lectura de páginas.",
        "keywords": ["busca", "investiga", "información", "noticias", "define", "definición",
                     "qué es", "quién es", "lee la página", "consulta"],
    },
    "MemoryAgent": {
        "description": "Maneja memoria y notas: recordar datos, preferencias, notas, proyectos.",
        "keywords": ["recuerda", "recordar", "guarda", "nota", "preferencia", "proyecto",
                     "qué sabes", "memoria"],
    },
    "VisionAgent": {
        "description": "Ve y analiza la pantalla del usuario.",
        "keywords": ["pantalla", "ves", "ver", "captura", "qué hay en", "analiza la imagen"],
    },
    "BrowserAgent": {
        "description": "Controla el navegador Chrome: buscar, navegar, hacer click, leer páginas, escribir en campos.",
        "keywords": ["navegador", "chrome", "página web", "sitio web", "abre en el navegador",
                     "haz click", "pestaña"],
    },
    "ComputerAgent": {
        "description": "Controla mouse, teclado y ventanas del sistema operativo directamente.",
        "keywords": ["mouse", "click en", "escribe en", "atajo", "teclado", "ventana",
                     "minimiza", "maximiza", "mueve el cursor"],
    },
    "FileAgent": {
        "description": "Gestiona archivos y carpetas: crear, mover, copiar, renombrar, buscar, organizar.",
        "keywords": ["archivo", "carpeta", "organiza", "mueve el archivo", "copia", "renombra",
                     "elimina el archivo", "busca archivos", "lee el archivo"],
    },
    "VoiceAgent": {
        "description": "Controla reproducción de música (Spotify) y voz.",
        "keywords": ["spotify", "música", "canción", "reproduce", "pausa", "volumen", "playlist"],
    },
    "SchedulerAgent": {
        "description": "Maneja tareas, eventos, recordatorios y el resumen diario.",
        "keywords": ["tarea", "evento", "recordatorio", "recuérdame", "agenda", "calendario",
                     "resumen del día"],
    },
    "ExecutionAgent": {
        "description": "Ejecuta comandos del sistema, abre aplicaciones, consulta información del sistema.",
        "keywords": ["abre la app", "ejecuta", "comando", "sistema", "hora es", "fecha"],
    },
}


def classify_agent(step_description: str) -> tuple[str, str]:
    """
    Determina qué agente especializado encaja mejor con un paso del plan,
    basándose en palabras clave. Si no hay coincidencia clara, devuelve un
    agente general sin restricciones — el comportamiento de siempre.
    """
    text = step_description.lower()
    best_agent = None
    best_score = 0

    for agent_name, info in AGENT_REGISTRY.items():
        score = sum(1 for kw in info["keywords"] if kw in text)
        if score > best_score:
            best_score = score
            best_agent = agent_name

    if best_agent and best_score > 0:
        return best_agent, AGENT_REGISTRY[best_agent]["description"]
    return "GeneralAgent", "Agente general, sin especialización para este paso."
