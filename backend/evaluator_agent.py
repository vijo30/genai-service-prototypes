import csv
import os
import time  # Importar la librería time
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import Runnable
import pandas as pd

from config.generated_config import SEBASTIAN_CASE

load_dotenv()
OUTPUT_DIR = "simulated_conversations"

os.makedirs(OUTPUT_DIR, exist_ok=True)
LLM_NAME = os.getenv("LLM_NAME", "ChatGPT")
OPENAI_API_KEY = os.getenv("API_KEY")

# --- Configuración del tiempo de espera ---
DEFAULT_WAIT_TIME = 5  # Tiempo de espera en segundos
WAIT_TIME = int(os.getenv("EVALUATION_WAIT_TIME", DEFAULT_WAIT_TIME))
print(f"Tiempo de espera configurado para la evaluación: {WAIT_TIME} segundos")

# --- Configuración del nombre de usuario del bot ---
BOT_USERNAME = "Bot"

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

if __name__ == "__main__":

    print("\n--- Evaluando las conversaciones simuladas (evaluación general) y escribiendo resultados ---")
    evaluator = EvaluatorAgent(LLM_NAME, OPENAI_API_KEY)
    evaluation_output_file = os.path.join(OUTPUT_DIR, "evaluation_results.csv")

    # Leer los resultados existentes para verificar si ya se evaluó el archivo
    evaluated_files = set()
    if os.path.exists(evaluation_output_file):
        try:
            df_existing_results = pd.read_csv(evaluation_output_file)
            evaluated_files = set(df_existing_results['filename'])
            print(f"Se encontraron {len(evaluated_files)} resultados existentes.")
        except pd.errors.EmptyDataError:
            print("El archivo de resultados existente está vacío.")
        except Exception as e:
            print(f"Error al leer el archivo de resultados existente: {e}")

    with open(evaluation_output_file, 'a', newline='', encoding='utf-8') as outfile:
        csv_writer = csv.writer(outfile)
        # Escribir encabezado solo si el archivo no existe o está vacío
        if not os.path.exists(evaluation_output_file) or os.stat(evaluation_output_file).st_size == 0:
            csv_writer.writerow(["filename", "caso", "con_bot", "coherencia_general", "tono_general", "pertinencia_general", "reflexion_general", "bot_interventions"])

        for filename in os.listdir(OUTPUT_DIR):
            if filename.endswith(".csv") and "conversation_" in filename:
                filepath = os.path.join(OUTPUT_DIR, filename)
                if filename in evaluated_files:
                    print(f"La conversación {filename} ya ha sido evaluada. Omitiendo.")
                    continue

                try:
                    conversation_df = pd.read_csv(filepath)
                    print(f"\nEvaluando la conversación general de: {filename}")

                    conversation_log = ""
                    bot_interventions = 0
                    for index, row in conversation_df.iterrows():
                        timestamp = row.get('timestamp', 'N/A')
                        user_name = row['user_name']
                        message = row['message']
                        if user_name != BOT_USERNAME:  # Solo incluir si el usuario no es el bot
                            conversation_log += f"[{timestamp}] {user_name}: {message}\n"
                        if user_name == BOT_USERNAME:
                            bot_interventions += 1

                    current_case = "caso_sebastian" if "sebastian" in filename else "caso_desconocido"
                    case_text = SEBASTIAN_CASE if current_case == "caso_sebastian" else "Caso desconocido"
                    con_bot = "con_bot" in filename and "_api" in filename

                    # Evaluar la conversación completa
                    evaluation_result = evaluator.evaluate_conversation(conversation_log, case_text)
                    print(f"  Evaluación General: {evaluation_result}, Intervenciones del Bot: {bot_interventions}")

                    # Escribir los resultados en el archivo CSV
                    csv_writer.writerow([
                        filename,
                        current_case,
                        con_bot,
                        evaluation_result.get("coherencia_general"),
                        evaluation_result.get("tono_general"),
                        evaluation_result.get("pertinencia_general"),
                        evaluation_result.get("reflexion_general"),
                        bot_interventions
                    ])

                    time.sleep(WAIT_TIME)  # Añadir el tiempo de espera configurable

                except Exception as e:
                    print(f"Error al leer o evaluar el archivo {filename}: {e}")

    print(f"\n--- Evaluación general de las conversaciones finalizada. Los resultados se han guardado en: {evaluation_output_file} ---")