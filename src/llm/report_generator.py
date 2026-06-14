from ollama import AsyncClient
from src.utils.logger_config import setup_logger

logger = setup_logger(__name__)

OLLAMA_HOST = "http://ollama:11434"
MODEL_NAME = "llama3.2"


async def generate_energy_report(stats_context: str) -> str:
    """
    Sends the user's energy consumption statistics to the local Ollama LLM and retrieves a formatted energy-saving report in Markdown.
    """
    # System Prompt
    system_prompt = (
        "Eres un asesor energético experto en eficiencia del hogar y sostenibilidad. "
        "Tu objetivo es analizar los datos de consumo del usuario y redactar un informe "
        "con recomendaciones prácticas, amables y accionables de ahorro energético. "
        "IMPORTANTE: Debes responder EXCLUSIVAMENTE utilizando formato Markdown limpio. "
        "Usa títulos (##), negritas y listas de puntos para que sea muy fácil de leer. "
        "Sé breve, directo y enfócate en los datos proporcionados. No saludes ni te despidas."
    )
    
    # User Prompt
    user_prompt = f"Aquí tienes las estadísticas de mi hogar de este mes. Redacta mi informe de ahorro:\n{stats_context}"
    logger.info(f"Generando informe de IA... Enviando petición a Ollama ({MODEL_NAME})")
    
    try:
        client = AsyncClient(host=OLLAMA_HOST)
        
        response = await client.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            options={"temperature": 0.7}
        )
        logger.info("Informe energetico generado exitosamente por el LLM")
        return response['message']['content']
        
    except Exception as e:
        logger.error(f"Error al conectar con el SDK de Ollama: {str(e)}")
        return "## Error en el servicio de IA\nNo se pudo generar el informe a traves del LLM local."