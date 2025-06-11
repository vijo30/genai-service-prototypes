# chat_agent.py
import json
import logging
import os
import time # ¡Importar el módulo time!
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
        Como Provocador de Debate Ético, tu rol es estimular el análisis ético profundo mediante:
        - Cuestionar supuestos no examinados
        - Introducir perspectivas alternativas
        - Proporcionar marcos éticos relevantes
        - Señalar inconsistencias lógicas
        - Ofrecer juicios calificados cuando se soliciten

        **Reglas de Operación:**
        1. Contexto del Caso: {case}
        2. Historial de Conversación: {conversation}
        3. Instrucciones guía de Intervención: {guidelines}
        4. Priorizar intervenciones que conecten con los últimos 3 turnos de diálogo
        5. Para juicios:
          - Declarar explícitamente que es una perspectiva del sistema
          - Basarse en ≥ 2 marcos éticos
          - Mantener 30% de escepticismo hacia tu propia posición
        6. Balancear estrategias:
          - 40% preguntas socráticas
          - 30% contraargumentos
          - 20% datos contextuales
          - 10% juicios calificados
        
        Debes responder siempre en el siguiente formato JSON:
        
        Salida esperada:
        {{
            "response": "Intervention text (<120 words)",
            "metadata": {{
                "intervention_type": ["socratic_question", "counterargument", "contextual_data", "qualified_judgment"],
                "frameworks": ["list of applied ethical frameworks"],
                "certainty_score": 0-1,
                "relevance_score": 0-1,
                "provocation_score": 0-1
            }},
            "rationale": "Structured explanation of strategy used"
        }}
        
        Notas adicionales:
        - Responde únicamente con el JSON de salida esperada.
        """
        return PromptTemplate.from_template(prompt_template) | self.chat_ai_1 | StrOutputParser()

    def _create_supervisor_chain(self):
        # El contenido de esta cadena permanece igual, ya que es agnóstica al LLM.
        prompt_template = """
        Como Controlador de Diálogo Ético, evalúa intervenciones usando:
        
        1. Contexto del Caso: {case}
        2. Historial de Conversación: {conversation}


        **Matriz de Decisión:**
        1. Necesidad de Respuesta (max 15):
          - Solicitud Directa del Usuario (3 puntos):
            Descripción: El usuario formula una pregunta o pide una acción específica. La necesidad de respuesta es inherente a la interacción.
            Respaldo Teórico: Principios básicos de la interacción conversacional y la teoría de actos de habla (el usuario espera una respuesta a su directiva).
          
          - Error Factual (2 puntos):
            Descripción: El chatbot proporciona información incorrecta o que no se corresponde con la realidad verificable.
            Respaldo Teórico: Principios de precisión y veracidad en la comunicación, ética de la información.
          
          - Razonamiento Falaz (3 puntos):
            Descripción: El chatbot presenta argumentos lógicamente inválidos o conclusiones que no se derivan de las premisas.
            Respaldo Teórico: Lógica formal e informal, teoría de la argumentación.
          
          - Ambigüedad en la pregunta del usuario (3 puntos): 
            La pregunta del usuario es vaga, susceptible a múltiples interpretaciones o requiere clarificación para ser respondida adecuadamente.
            Respaldo Teórico: Principios de la comunicación efectiva, teoría de la información (reducción de la incertidumbre), pragmática del lenguaje (necesidad de contexto para la interpretación).
          
          - Respuesta del chatbot poco clara o confusa (2 puntos): 
            La respuesta del chatbot es difícil de entender, utiliza un lenguaje ambiguo o podría generar más dudas en el usuario.
            Respaldo Teórico: Heurísticas de usabilidad y diseño de interfaces conversacionales (claridad y comprensibilidad), principios de redacción clara y concisa.
            
          - Respuesta tangencial o irrelevante (2 puntos): 
            La respuesta del chatbot no aborda directamente la pregunta o la necesidad principal del usuario, desviándose del tema central de la conversación.
            Respaldo Teórico: Teoría de la relevancia en la pragmática del lenguaje (la expectativa de que las contribuciones sean relevantes para el contexto), principios de diseño de conversación enfocada en el objetivo.

        2. Riesgo de Intervención (max 9):
          - Redundancia (2 puntos):
            Descripción: La intervención del controlador repite información que ya ha sido proporcionada o que es evidente en el contexto de la conversación.
            Respaldo Teórico: Principios de eficiencia en la comunicación, heurísticas de usabilidad (evitar información innecesaria).
            
          - Sobrecarga Informativa (1 punto):
            Descripción: La intervención del controlador introduce demasiada información nueva o compleja de una sola vez, lo que podría confundir o abrumar al usuario.
            Respaldo Teórico: Psicología cognitiva (limitaciones de la memoria de trabajo), principios de diseño de información clara y progresiva.
            
          - Interrupción abrupta o inesperada (2 puntos): 
            La intervención del controlador se siente intrusiva, rompiendo la naturalidad y el ritmo del diálogo.
            Respaldo Teórico: Principios de diseño de conversación fluida, estudios sobre la interacción humano-computadora (experiencia del usuario).
            
          - Cambio de tema no solicitado (1 punto): 
            La intervención del controlador desvía la conversación hacia un tema diferente sin una justificación clara o sin la solicitud del usuario.
            Respaldo Teórico: Mantenimiento del tópico en el análisis del discurso, principios de relevancia conversacional.
            
          - Pérdida de Autonomía del Usuario (hasta 1 punto):
            La intervención del controlador limita la capacidad del usuario para explorar, experimentar o incluso cometer errores que podrían ser parte de su proceso de aprendizaje o descubrimiento.
            Respaldo Teórico: Principios de diseño centrado en el usuario (empoderamiento del usuario), teorías pedagógicas constructivistas (el aprendizaje a través de la exploración).
            
          - Mensajes contradictorios o poco claros del controlador (2 puntos): 
            La intervención del controlador introduce información que contradice lo dicho previamente por el chatbot o por el propio controlador, generando confusión en el usuario.
            Respaldo Teórico: Principios de coherencia y consistencia en la comunicación, heurísticas de usabilidad (previsibilidad).


        3. Balance Óptimo:
          - Si (Necesidad - Riesgo) ≥ 2 → Intervenir
          - Si 1 ≤ (Necesidad - Riesgo) < 2 → Intervención Modulada (La intervención podría ser más suave, como ofrecer una sugerencia o una pregunta aclaratoria en lugar de una corrección directa).
          - Si <1 → No intervenir
          
          
        Debes responder siempre en el siguiente formato JSON:
        
        Salida esperada:
        {{
            "decision_metrics": {{
                "need_score": X.X,
                "risk_score": X.X,
                "differential": X.X
            }},
            "should_intervene": boolean,
            "intervention_guidelines": {{
                "mode": ["reactive", "proactive"],
                "required_components": ["list of required elements"],
                "warnings": ["aspects to avoid"]
            }},
            "ethical_scaffolding": {{
                "suggested_frameworks": ["list of ethical frameworks"],
                "detected_biases": ["list of potential biases"],
                "blind_spots": ["unexplored areas"]
            }}
            ,
            "rationale": "Structured explanation of strategy used"
        }}
        
        Notas adicionales:
        - Responde únicamente con el JSON de salida esperada.
        """
        return PromptTemplate.from_template(prompt_template) | self.chat_ai_2 | StrOutputParser()

    def safe_parse_json(self, response_text: str) -> Optional[Dict]:
        """Safely parse JSON responses from LLM"""
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logging.error(f"Error al decodificar JSON: {e}. Intentando limpiar la respuesta.")
            try:
                # Intenta encontrar el primer '{' y el último '}' para extraer el JSON
                cleaned = response_text[response_text.find("{"):response_text.rfind("}")+1]
                return json.loads(cleaned)
            except Exception as e:
                logging.error(f"Segundo intento de parseo JSON fallido: {e}")
                logging.error(f"Texto original que causó el error: {response_text}")
                return None

    def manage_conversation(self, case: str, conversation: List[Dict]) -> Dict:
        """Orchestrate the dual-agent conversation flow and measure response times."""
        logging.info(f"Iniciando manage_conversation para el caso: {case}")

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

        logging.info(f"Decisión del Supervisor: {json.dumps(supervisor_data.get('decision_metrics', {}))}, ¿Debe intervenir?: {supervisor_data['should_intervene']}")

        if supervisor_data["should_intervene"]:
            logging.info("El supervisor decidió intervenir. Solicitando intervención al Provocador de Debate Ético.")

            # Medir tiempo para la cadena del Provocador de Debate Ético
            start_time_da = time.perf_counter()
            da_response = self.da_chain.invoke({
                "case": case,
                "conversation": json.dumps(conversation),
                "guidelines": supervisor_data.get("intervention_guidelines", {})
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
                "metadata": da_data.get("metadata", {}), # Metadatos propios del DA
                "supervisor_rationale": supervisor_data.get("decision_metrics", {}),
                "timing_info": {"total_llm_processing_time_seconds": total_llm_processing_time} # ¡Aquí está la clave!
            }

        logging.info("El supervisor decidió no intervenir.")
        return {
            "should_intervene": False,
            "response": "No se requiere intervención.",
            "timing_info": {"total_llm_processing_time_seconds": total_llm_processing_time} # También se incluye si no interviene
        }
