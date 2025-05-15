import json
import logging
import os
from typing import Dict, List, Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv() 

class EthicalDebateAgent:
    def __init__(self):
        self.API_KEY = os.getenv("API_KEY")
        self.LLM_NAME = os.getenv("LLM_NAME")
        self._initialize_models()
        self._setup_chains()
        
    def _initialize_models(self):
        """Initialize the LLM models based on configuration"""
        if self.LLM_NAME == 'ChatGPT':
            self.chat_ai_1 = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, api_key=self.API_KEY)
            self.chat_ai_2 = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, api_key=self.API_KEY)
        elif self.LLM_NAME == 'Gemini':
            self.chat_ai_1 = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.7, api_key=self.API_KEY)
            self.chat_ai_2 = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.3, api_key=self.API_KEY)
        else:
            raise ValueError("Unsupported LLM configuration")

    def _setup_chains(self):
        """Setup the prompt chains for both agents"""
        self.da_chain = self._create_devils_advocate_chain()
        self.supervisor_chain = self._create_supervisor_chain()
        
    def _create_devils_advocate_chain(self):
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
        prompt_template = """
        Como Controlador de Diálogo Ético, evalúa intervenciones usando:
        
        1. Contexto del Caso: {case}
        2. Historial de Conversación: {conversation}


        **Matriz de Decisión:**
        1. Necesidad de Respuesta (max 8):
          - Solicitud directa del usuario = 3
          - Error factual = 2
          - Razonamiento falaz = 3


        2. Riesgo de Intervención (max 3):
          - Redundancia = 2
          - Sobrecarga informativa = 1


        3. Balance Óptimo:
          - Si (Necesidad - Riesgo) ≥ 2 → Intervenir
          - Si 1 ≤ (Necesidad - Riesgo) < 2 → Intervención Modulada
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
        except json.JSONDecodeError:
            try:
                cleaned = response_text[response_text.find("{"):response_text.rfind("}")+1]
                return json.loads(cleaned)
            except Exception as e:
                logging.error(f"JSON parsing error: {e}")
                return None

    def manage_conversation(self, case: str, conversation: List[Dict]) -> Dict:
        """Orchestrate the dual-agent conversation flow"""
        supervisor_response = self.supervisor_chain.invoke({
            "case": case,
            "conversation": json.dumps(conversation),
        })
        supervisor_data = self.safe_parse_json(supervisor_response)
        print(supervisor_data, flush=True)
        if not supervisor_data:
            return {"should_intervene": False, "response": ""}

        if supervisor_data["should_intervene"]:
          
            da_response = self.da_chain.invoke({
                "case": case,
                "conversation": json.dumps(conversation),
                "guidelines": supervisor_data.get("intervention_guidelines", {})
            })
            
            da_data = self.safe_parse_json(da_response)
            print(da_data, flush=True)
            return {
                "should_intervene": True,
                "response": da_data.get("response", ""),
                "metadata": da_data.get("metadata", {}),
                "supervisor_rationale": supervisor_data.get("decision_metrics", {})
            }
        
        return {"should_intervene": False, "response": ""}

ethical_agent = EthicalDebateAgent()