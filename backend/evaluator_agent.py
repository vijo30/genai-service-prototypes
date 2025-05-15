from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import Runnable

class EvaluatorAgent:
    """Agente evaluador de la calidad y características GENERALES de la conversación en debates éticos."""

    def __init__(self, llm_name: str, api_key: str):
        self.llm_name = llm_name
        self.api_key = api_key
        self.llm = self.initialize_llm()
        self.output_parser = JsonOutputParser()
        self.evaluation_chain = self.build_evaluation_chain()

    def initialize_llm(self):
        """Inicializa el modelo de lenguaje adecuado con temperatura 0 para evaluaciones determinísticas."""
        if self.llm_name == 'ChatGPT':
            return ChatOpenAI(model="gpt-3.5-turbo", temperature=0, api_key=self.api_key)
        elif self.llm_name == 'Gemini':
            return ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0, google_api_key=self.api_key)
        else:
            raise ValueError(f"Modelo de lenguaje no soportado: {self.llm_name}")

    def build_evaluation_chain(self) -> Runnable:
        """Construye la cadena para evaluar la conversación completa con sustento teórico."""
        prompt = ChatPromptTemplate.from_messages([
            HumanMessagePromptTemplate.from_template(
                """
                Eres un evaluador experto en debates éticos y dinámicas de conversación en línea. Tu tarea es analizar la calidad y las características GENERALES de la siguiente conversación
                en el contexto de un debate sobre un dilema ético.

                **HISTORIAL DE CONVERSACIÓN:**
                "{conversation_log}"

                **CONTEXTO DEL CASO:**
                {case}

                Para realizar tu evaluación general, considera los siguientes criterios, basados en principios de la teoría de la argumentación, la ética comunicativa y la psicología social:

                1.  **Coherencia Argumentativa General (Escala 1-5):** Evalúa si la conversación en su conjunto presenta un desarrollo lógico de los argumentos, con conexiones claras entre las intervenciones. Considera si los participantes construyen sobre las ideas de los demás de manera coherente.
                    * **Sustento Teórico:** Se relaciona con la teoría de la argumentación y la construcción colaborativa del conocimiento en diálogos (Walton & Krabbe, 1995). Una conversación coherente muestra una progresión lógica de los puntos de vista y una consideración mutua de los argumentos.

                2.  **Tono Ético General (Escala 1-5, donde 1 es altamente ético y 5 es altamente problemático):** Evalúa la orientación ética predominante en la conversación. Considera la frecuencia y el impacto de los mensajes éticos versus los problemáticos, la presencia de empatía, respeto y la consideración de valores a lo largo del debate.
                    * **Sustento Teórico:** Vinculado a la ética comunicativa (Habermas, 1990) aplicada al nivel de la interacción grupal. Una conversación éticamente orientada promueve la comprensión mutua y el respeto por las normas de la comunicación racional.

                3.  **Pertinencia General al Caso (Escala 1-5):** Evalúa si la conversación se mantuvo enfocada en el dilema ético presentado en el caso a lo largo de su desarrollo. Considera la proporción de mensajes que contribuyen directamente a la discusión del caso versus aquellos que se desvían del tema central.
                    * **Sustento Teórico:** Relacionado con la teoría de la relevancia y el mantenimiento del foco en la tarea comunicativa (Sperber & Wilson, 1986). Una conversación pertinente asegura que el esfuerzo comunicativo se dirija al problema ético en cuestión.

                4.  **Nivel Reflexivo General (Escala 1-5, donde 1 es altamente reflexivo y 5 es superficial/cínico):** Evalúa la profundidad general del pensamiento y la consideración de las implicaciones éticas a lo largo de la conversación. Considera la presencia de análisis profundos, la exploración de diferentes perspectivas y la consideración de las consecuencias de las decisiones éticas.
                    * **Sustento Teórico:** Conectado al pensamiento crítico colectivo y la capacidad del grupo para la deliberación moral (Thompson, 2008). Una conversación reflexiva implica una exploración seria y considerada del dilema ético.

                Devuelve tu evaluación general en formato JSON con las siguientes claves: "coherencia_general", "tono_general", "pertinencia_general", "reflexion_general".
                Asegúrate de que los valores sean números enteros entre 1 y 5.
                """
            )
        ])
        return prompt | self.llm | self.output_parser

    def evaluate_conversation(self, conversation_log: str, case: str):
        """Evalúa el historial completo de la conversación dado el contexto del caso y devuelve la evaluación general en formato JSON."""
        return self.evaluation_chain.invoke({
            "conversation_log": conversation_log,
            "case": case
        })