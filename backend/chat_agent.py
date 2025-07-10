# chat_agent.py
import json
import logging
import os
import time # ¡Importar el módulo time!
import re
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Importar los modelos de Langchain
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_deepseek import ChatDeepSeek

from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Configuración del logging para ver errores si los hay
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Cargar las variables de entorno desde .env
load_dotenv(override=True) 

class EthicalDebateAgent:
    def __init__(self, llm_choice: str = "ChatGPT"):
        """
        Inicializa el EthicalDebateAgent con una elección específica de LLM.
        
        Args:
            llm_choice (str): Elige el LLM a usar: "ChatGPT", "Gemini", o "DeepSeek".
        """
        self.llm_choice = llm_choice
        
        # Cargar todas las posibles API keys
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        
        self._initialize_models()
        self._setup_chains()
        
    def _initialize_models(self):
        """Inicializa los modelos LLM basándose en la configuración `llm_choice`."""
        if self.llm_choice == 'ChatGPT':
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY no está configurada en las variables de entorno para ChatGPT.")
            self.chat_ai_1 = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, api_key=self.openai_api_key)
            self.chat_ai_2 = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, api_key=self.openai_api_key)
            logging.info("Modelos inicializados: ChatGPT (gpt-4o-mini)")
        
        elif self.llm_choice == 'Gemini':
            if not self.google_api_key:
                raise ValueError("GOOGLE_API_KEY no está configurada en las variables de entorno para Gemini.")
            self.chat_ai_1 = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.7, api_key=self.google_api_key)
            self.chat_ai_2 = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.3, api_key=self.google_api_key)
            logging.info("Modelos inicializados: Gemini (gemini-2.0-flash)")
            
        elif self.llm_choice == 'DeepSeek':
            if not self.deepseek_api_key:
                raise ValueError("DEEPSEEK_API_KEY no está configurada en las variables de entorno para DeepSeek.")
            # Usando ChatDeepSeek directamente
            self.chat_ai_1 = ChatDeepSeek(
                model="deepseek-chat", 
                temperature=0.7, 
                api_key=self.deepseek_api_key
            )
            self.chat_ai_2 = ChatDeepSeek(
                model="deepseek-chat", 
                temperature=0.3, 
                api_key=self.deepseek_api_key
            )
            logging.info("Modelos inicializados: DeepSeek (deepseek-chat)")
            
        else:
            raise ValueError(
                f"Configuración de LLM no soportada: '{self.llm_choice}'. "
                "Las opciones válidas son 'ChatGPT', 'Gemini', 'DeepSeek'."
            )

    def _setup_chains(self):
        """Setup the prompt chains for both agents"""
        self.da_chain = self._create_devils_advocate_chain()
        self.supervisor_chain = self._create_supervisor_chain()
        
    def _create_devils_advocate_chain(self):
        # El contenido de esta cadena permanece igual, ya que es agnóstica al LLM.
        prompt_template = """
        Eres un Provocador de Debate Ético. Tu rol es romper el estancamiento argumentativo detectado. Tu intervención debe ser una acción estratégica, breve y directa (menos de 80 palabras).

        Contexto del Caso: {case}
        Historial de Conversación: {conversation}
        
        Sigue esta JERARQUÍA DE ESTRATEGIAS para formular tu intervención. Usa la primera estrategia que sea aplicable y relevante:

        1.  **PRIORIDAD 1 (La más suave): HAZ UNA PREGUNTA SOCRÁTICA.** Cuestiona un supuesto fundamental que el grupo está dando por sentado o pide una definición más profunda de un concepto clave que usan (ej: 'justicia', 'deber').
            *Ejemplo: "Estamos asumiendo que el objetivo principal es X. ¿Hay algún otro valor fundamental que podríamos estar pasando por alto?"*

        2.  **PRIORIDAD 2 (Si una pregunta no es suficiente): PRESENTA UNA PERSPECTIVA ALTERNATIVA.** Introduce el punto de vista de una parte interesada que no ha sido considerada por el grupo.
            *Ejemplo: "Desde la perspectiva de [la familia del afectado / la comunidad / la empresa], ¿cómo se vería esta decisión?"*

        3.  **PRIORIDAD 3 (El último recurso): SEÑALA UNA INCONSISTENCIA LÓGICA.** Si hay una contradicción clara en los últimos mensajes, señálala de forma neutral para que el grupo la resuelva.
            *Ejemplo: "Noto que al principio se argumentó A, pero la propuesta actual B parece contradecir ese punto. ¿Podemos aclarar esta aparente inconsistencia?"*

        **INSTRUCCIÓN:** Genera únicamente el texto de tu intervención. No incluyas el nombre de la estrategia, ni metadatos, ni explicaciones. Solo el mensaje que se enviará al chat.
        
        Debes responder siempre en el siguiente formato JSON:
        
        Salida esperada:
        {{
            "response": "Intervention text"
        }}
        
        Notas adicionales:
        - Responde únicamente con el JSON de salida esperada.
        """
        return PromptTemplate.from_template(prompt_template) | self.chat_ai_1 | StrOutputParser()

    def _create_supervisor_chain(self):
        # El contenido de esta cadena permanece igual, ya que es agnóstica al LLM.
        prompt_template = """
        Eres un Controlador de Diálogo Ético. Tu única función es determinar si la conversación actual muestra signos de ESTANCAMIENTO ARGUMENTATIVO.
        Analiza el contexto del caso y el historial de la conversación.

        Contexto del Caso: {case}
        Historial de Conversación: {conversation}

        Ahora, responde a la siguiente pregunta basándote ESTRICTAMENTE en si se cumple AL MENOS UNA de las siguientes condiciones:

        1.  **CONSENSO PREMATURO:** ¿Múltiples participantes han expresado acuerdo con la primera o segunda solución propuesta sin que se haya presentado una alternativa significativa?
        2.  **REPETICIÓN DE IDEAS:** ¿Se están repitiendo los mismos argumentos o frases sin añadir nueva información o profundidad?
        3.  **FALACIA LÓGICA EVIDENTE:** ¿Se ha utilizado un ataque personal (ad hominem) o una generalización burda y sin fundamento?
        4.  **PREGUNTA CLAVE IGNORADA:** ¿Un participante hizo una pregunta relevante que fue ignorada por los demás en los turnos siguientes?

        **PREGUNTA:** ¿Se ha detectado estancamiento argumentativo según los criterios anteriores?

        **RESPUESTA:** Responde únicamente en el apartado "should_intervene". No añadas ninguna explicación o texto adicional.
          
        Debes responder siempre en el siguiente formato JSON:
        
        Salida esperada:
        {{
            "should_intervene": boolean
        }}
        
        Notas adicionales:
        - Responde únicamente con el JSON de salida esperada.
        """
        return PromptTemplate.from_template(prompt_template) | self.chat_ai_2 | StrOutputParser()

    def safe_parse_json(self, response_text: str) -> Optional[Dict]:
        """
        Extrae y parsea de forma robusta un objeto JSON de un string,
        incluso si está envuelto en texto o bloques de código Markdown.
        """
        if not isinstance(response_text, str):
            return None

        # Expresión regular para encontrar un bloque JSON (empieza con { y termina con })
        # re.DOTALL hace que '.' coincida también con saltos de línea
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        
        if match:
            json_str = match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logging.error(f"Fallo el parseo de JSON extraído: {e}. JSON String: '{json_str}'")
                return None
        else:
            logging.error(f"No se encontró un objeto JSON válido en la respuesta. Respuesta completa: '{response_text}'")
            return None

    def manage_conversation(self, case: str, conversation: List[Dict]) -> Dict:
        """Orchestrate the dual-agent conversation flow and measure response times."""
        logging.info(f"Iniciando manage_conversation")

        total_llm_processing_time = 0.0 # Inicializar el contador de tiempo total

        # Medir tiempo para la cadena del Supervisor
        start_time_supervisor = time.perf_counter()
        supervisor_response = self.supervisor_chain.invoke({
            "case": case,
            "conversation": json.dumps(conversation),
        })
        end_time_supervisor = time.perf_counter()
        total_llm_processing_time += (end_time_supervisor - start_time_supervisor)

        supervisor_data = self.safe_parse_json(supervisor_response)

        if not supervisor_data:
            logging.warning("Supervisor no pudo generar una respuesta JSON válida. No se intervendrá.")
            return {
                "should_intervene": False,
                "response": "Error: Supervisor no pudo generar una respuesta válida.",
                "timing_info": {"total_llm_processing_time_seconds": total_llm_processing_time} # Aquí ya se incluye el tiempo
            }

        logging.info(f"Decisión del Supervisor: ¿Debe intervenir?: {supervisor_data['should_intervene']}")

        if supervisor_data["should_intervene"]:
            logging.info("El supervisor decidió intervenir. Solicitando intervención al Provocador de Debate Ético.")

            # Medir tiempo para la cadena del Provocador de Debate Ético
            start_time_da = time.perf_counter()
            da_response = self.da_chain.invoke({
                "case": case,
                "conversation": json.dumps(conversation),
            })
            end_time_da = time.perf_counter()
            total_llm_processing_time += (end_time_da - start_time_da) # Suma el tiempo del DA

            da_data = self.safe_parse_json(da_response)

            if not da_data:
                logging.warning("Provocador de Debate Ético no pudo generar una respuesta JSON válida.")
                return {
                    "should_intervene": False,
                    "response": "Error: Provocador no pudo generar una respuesta válida.",
                    "timing_info": {"total_llm_processing_time_seconds": total_llm_processing_time} # Aquí se incluye el tiempo total
                }

            logging.info(f"Respuesta del Provocador: {da_data.get('response', '')}")
            return {
                "should_intervene": True,
                "response": da_data.get("response", ""),
                "timing_info": {"total_llm_processing_time_seconds": total_llm_processing_time} # ¡Aquí está la clave!
            }

        logging.info("El supervisor decidió no intervenir.")
        return {
            "should_intervene": False,
            "response": "No se requiere intervención.",
            "timing_info": {"total_llm_processing_time_seconds": total_llm_processing_time} # También se incluye si no interviene
        }
