import csv
import os
import time
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_deepseek import ChatDeepSeek
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import Runnable
from langchain_core.exceptions import OutputParserException # Importar para manejar errores de parseo
import pandas as pd
import re # Asegurar la importación de 're'
from datetime import datetime # Asegurar la importación de datetime

from config.generated_config import SEBASTIAN_CASE # Asegúrate de que esta importación sea correcta

load_dotenv(override=True)
OUTPUT_DIR = "simulated_conversations"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Configuración del LLM para el evaluador
EVALUATOR_LLM_NAME = os.getenv("EVALUATOR_LLM_NAME", "Gemini") 
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# --- Configuración del tiempo de espera ---
DEFAULT_WAIT_TIME = 5 
WAIT_TIME = int(os.getenv("EVALUATION_WAIT_TIME", DEFAULT_WAIT_TIME))
print(f"Tiempo de espera configurado para la evaluación: {WAIT_TIME} segundos")

# --- Configuración del nombre de usuario del bot ---
BOT_USERNAME = "Bot"

class EvaluatorAgent:
    """Agente evaluador de la calidad y características GENERALES de la conversación en debates éticos,
    y de la calidad de las intervenciones específicas del bot."""

    def __init__(self, llm_name: str):
        self.llm_name = llm_name
        self.llm = self.initialize_llm()
        self.output_parser = JsonOutputParser()
        self.holistic_evaluation_chain = self.build_holistic_evaluation_chain()
        self.intervention_decision_chain = self.build_intervention_decision_chain()
        self.intervention_quality_chain = self.build_intervention_quality_chain()

    def initialize_llm(self):
        """Inicializa el modelo de lenguaje adecuado con temperatura 0 para evaluaciones determinísticas."""
        if self.llm_name == 'ChatGPT':
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY no está configurada para el evaluador ChatGPT.")
            return ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY)
        elif self.llm_name == 'Gemini':
            if not GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY no está configurada para el evaluador Gemini.")
            return ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0, google_api_key=GOOGLE_API_KEY)
        elif self.llm_name == 'DeepSeek':
            if not DEEPSEEK_API_KEY:
                raise ValueError("DEEPSEEK_API_KEY no está configurada para el evaluador DeepSeek.")
            return ChatDeepSeek(model="deepseek-chat", temperature=0, api_key=DEEPSEEK_API_KEY)
        else:
            raise ValueError(f"Modelo de lenguaje no soportado para el evaluador: {self.llm_name}")

    def build_holistic_evaluation_chain(self) -> Runnable:
        """Construye la cadena para evaluar la conversación completa con sustento teórico."""
        prompt = ChatPromptTemplate.from_messages([
            HumanMessagePromptTemplate.from_template(
                """
                Eres un evaluador experto en debates éticos y dinámicas de conversación en línea. Tu tarea es analizar la calidad y las características GENERALES de la siguiente conversación
                en el contexto de un debate sobre un dilema ético.

                **HISTORIAL DE CONVERSACIÓN COMPLETO:**
                "{conversation_log}"

                **CONTEXTO DEL CASO:**
                {case}

                Para realizar tu evaluación general, considera los siguientes criterios, basados en principios de la teoría de la argumentación, la ética comunicativa y la psicología social:

                1.  **Coherencia Argumentativa General (Escala 1-5):** Evalúa si la conversación en su conjunto presenta un desarrollo lógico de los argumentos, con conexiones claras entre las intervenciones. Considera si los participantes construyen sobre las ideas de los demás de manera coherente.
                    *   **Sustento Teórico:** Se relaciona con la teoría de la argumentación y la construcción colaborativa del conocimiento en diálogos (Walton & Krabbe, 1995). Una conversación coherente muestra una progresión lógica de los puntos de vista y una consideración mutua de los argumentos.

                2.  **Tono Ético General (Escala 1-5, donde 1 es altamente ético y 5 es altamente problemático/no ético):** Evalúa la orientación ética predominante en la conversación. Considera la frecuencia y el impacto de los mensajes éticos versus los problemáticos, la presencia de empatía, respeto y la consideración de valores a lo largo del debate.
                    *   **Sustento Teórico:** Vinculado a la ética comunicativa (Habermas, 1990) aplicada al nivel de la interacción grupal. Una conversación éticamente orientada promueve la comprensión mutua y el respeto por las normas de la comunicación racional.

                3.  **Pertinencia General al Caso (Escala 1-5):** Evalúa si la conversación se mantuvo enfocada en el dilema ético presentado en el caso a lo largo de su desarrollo. Considera la proporción de mensajes que contribuyen directamente a la discusión del caso versus aquellos que se desvían del tema central.
                    *   **Sustento Teórico:** Relacionado con la teoría de la relevancia y el mantenimiento del foco en la tarea comunicativa (Sperber & Wilson, 1986). Una conversación pertinente asegura que el esfuerzo comunicativo se dirija al problema ético en cuestión.

                4.  **Nivel Reflexivo General (Escala 1-5, donde 1 es altamente reflexivo y 5 es superficial/cínico):** Evalúa la profundidad general del pensamiento y la consideración de las implicaciones éticas a lo largo de la conversación. Considera la presencia de análisis profundos, la exploración de diferentes perspectivas y la consideración de las consecuencias de las decisiones éticas.
                    *   **Sustento Teórico:** Conectado al pensamiento crítico colectivo y la capacidad del grupo para la deliberación moral (Thompson, 2008). Una conversación reflexiva implica una exploración seria y considerada del dilema ético.

                **Salida JSON esperada:**
                ```json
                {{
                    "coherencia_general": 1-5,
                    "tono_general": 1-5,
                    "pertinencia_general": 1-5,
                    "reflexion_general": 1-5
                }}
                ```
                **ES CRÍTICO:** SIEMPRE devuelve un JSON válido con TODAS las claves y valores numéricos. Si por alguna razón no puedes asignar un score, usa 0 o 1. No incluyas texto explicativo fuera del JSON.
                """
            )
        ])
        return prompt | self.llm | self.output_parser

    def build_intervention_decision_chain(self) -> Runnable:
        """Construye la cadena para evaluar si el bot debió o no intervenir."""
        prompt = ChatPromptTemplate.from_messages([
            HumanMessagePromptTemplate.from_template(
                """
                Eres un evaluador experto en debates éticos. Tu tarea es decidir si el 'Provocador de Debate Ético' (el bot) DEBIÓ haber intervenido en un punto específico de la conversación.

                **CONTEXTO DE LA CONVERSACIÓN (Últimos turnos, ANTES de la decisión del bot):**
                {context_history}
                
                Si el contexto está vacío ("No hay historial previo" o similar), asume que es el primer mensaje de la conversación y evalúa si la primera intervención del bot fue necesaria o si el bot debió haber intervenido si el primer mensaje lo ameritaba.

                **MENSAJE DEL BOT (si lo hubo) o INDICACIÓN DE NO INTERVENCIÓN:**
                {bot_turn_content}

                **Considera las reglas del Supervisor del bot para la intervención (basadas en Necesidad - Riesgo):**
                - Intervención necesaria si hay: Solicitud Directa del Usuario, Error Factual, Razonamiento Falaz, Ambigüedad en pregunta, Respuesta previa poco clara/confusa, Respuesta tangencial/irrelevante.
                - Riesgos a evitar: Redundancia, Sobrecarga Informativa, Interrupción Abrupta, Cambio de Tema No Solicitado, Pérdida de Autonomía del Usuario, Mensajes Contradictorios.
                - El bot solo debe intervenir si (Necesidad - Riesgo) ≥ 2.

                Basado en el `context_history` y el `bot_turn_content` (que puede ser el mensaje del bot o la indicación de que no intervino), ¿el bot DEBIÓ haber intervenido en este punto (independientemente de si lo hizo o no)?
                Responde 'SI' o 'NO' y justifica brevemente tu decisión.

                **Salida JSON esperada:**
                ```json
                {{
                    "should_have_intervened_evaluator": "SI/NO",
                    "rationale": "Breve justificación de la decisión del evaluador."
                }}
                ```
                **ES CRÍTICO:** SIEMPRE devuelve un JSON válido con las claves y valores especificados, incluso si la justificación es "No puedo evaluar por falta de contexto" o si el valor de "should_have_intervened_evaluator" es "NO". No incluyas texto explicativo fuera del JSON.
                """
            )
        ])
        return prompt | self.llm | self.output_parser

    def build_intervention_quality_chain(self) -> Runnable:
        """Construye la cadena para evaluar la calidad de una intervención específica del bot."""
        prompt = ChatPromptTemplate.from_messages([
            HumanMessagePromptTemplate.from_template(
                """
                Eres un evaluador experto en debates éticos. Tu tarea es evaluar la **calidad intrínseca** de la siguiente intervención del 'Provocador de Debate Ético' (el bot), ASUMIENDO que la intervención fue necesaria.

                **CONTEXTO DE LA CONVERSACIÓN (Últimos turnos antes de esta intervención):**
                {context_history}

                **INTERVENCIÓN DEL BOT A EVALUAR:**
                {bot_intervention_text}

                **METADATOS DE LA INTERVENCIÓN (si disponibles):**
                {bot_metadata_json}

                **GUÍAS DE INTERVENCIÓN DEL SUPERVISOR (si disponibles, parte de los metadatos):**
                {supervisor_guidelines_json}

                Evalúa esta intervención del bot basándote en los siguientes criterios, asignando un score de 1 (malo) a 5 (excelente) para cada uno:

                1.  **Claridad y Concisión:** ¿El mensaje es fácil de entender, directo y no redundante?
                2.  **Relevancia Inmediata:** ¿El mensaje aborda directamente el último turno o los puntos clave de la conversación reciente?
                3.  **Profundidad de Provocación Ética:** ¿El mensaje logra estimular un análisis ético más profundo, cuestionar supuestos clave, o introducir perspectivas relevantes? (Alineado con el rol del DA).
                4.  **Adherencia a Guías del Supervisor:** ¿El contenido y la forma de la intervención respetan las "intervention_guidelines" y evitan las "warnings" sugeridas por el Supervisor? (Ej: "modo": "reactive", "required_components": [...]).
                5.  **Cumplimiento del Rol del DA:** ¿El mensaje se alinea con las estrategias del "Provocador de Debate Ético" (ej. 40% preguntas socráticas, 30% contraargumentos, etc.) y las restricciones (ej. <120 palabras, uso explícito de ≥ 2 marcos éticos para juicios)?

                **Salida JSON esperada:**
                ```json
                {{
                    "clarity_score": 1-5,
                    "relevance_score": 1-5,
                    "depth_score": 1-5,
                    "adherence_score": 1-5,
                    "role_compliance_score": 1-5,
                    "overall_quality_rationale": "Breve explicación general de la calidad de esta intervención."
                }}
                ```
                **ES CRÍTICO:** SIEMPRE devuelve un JSON válido con las claves especificadas y valores numéricos para los scores (1-5 o 0 si no se puede evaluar), incluso si la justificación es "No se pudo evaluar" o si la calidad es baja. No incluyas texto explicativo fuera del JSON.
                """
            )
        ])
        return prompt | self.llm | self.output_parser

    def evaluate_conversation_holistic(self, conversation_log: str, case: str):
        """Evalúa el historial completo de la conversación y devuelve la evaluación general."""
        try:
            return self.holistic_evaluation_chain.invoke({
                "conversation_log": conversation_log,
                "case": case
            })
        except OutputParserException as e:
            print(f"ADVERTENCIA: Fallo de parseo JSON en evaluación holística. Error: {e.llm_output}")
            return {
                "coherencia_general": 0, "tono_general": 0,
                "pertinencia_general": 0, "reflexion_general": 0
            } # Devolver valores por defecto

    def evaluate_all_simulated_conversations(self):
        """
        Itera sobre todos los archivos de conversación simulada, los evalúa y guarda los resultados.
        """
        print("\n--- Evaluando las conversaciones simuladas y escribiendo resultados ---")
        evaluation_output_file = os.path.join(OUTPUT_DIR, "evaluation_results.csv")

        # Verificar y cargar resultados existentes
        evaluated_files = set()
        existing_results_df = pd.DataFrame()
        if os.path.exists(evaluation_output_file) and os.stat(evaluation_output_file).st_size > 0:
            try:
                existing_results_df = pd.read_csv(evaluation_output_file)
                evaluated_files = set(existing_results_df['filename'])
                print(f"Se encontraron {len(evaluated_files)} resultados existentes.")
            except pd.errors.EmptyDataError:
                print("El archivo de resultados existente está vacío. Se creará uno nuevo.")
            except Exception as e:
                print(f"Error al leer el archivo de resultados existente: {e}")
                existing_results_df = pd.DataFrame() # Reset para no usar datos corruptos

        # Definir el encabezado de las columnas
        fieldnames = [
            "filename", "caso", "bot_llm_choice", "user_llm_choice", "con_bot",
            "coherencia_general", "tono_general", "pertinencia_general", "reflexion_general",
            "total_interventions", "vp_count", "fp_count", "fn_count", "vn_count",
            "precision", "recall", "f1_score",
            "avg_quality_clarity", "avg_quality_relevance", "avg_quality_depth",
            "avg_quality_adherence", "avg_quality_role_compliance",
            "avg_processing_time_seconds"
        ]

        # Abrir el archivo en modo append. Si no existe, se creará.
        # Solo escribir el encabezado si el archivo está vacío
        file_exists_and_not_empty = os.path.exists(evaluation_output_file) and os.stat(evaluation_output_file).st_size > 0
        with open(evaluation_output_file, 'a', newline='', encoding='utf-8') as outfile:
            csv_writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            if not file_exists_and_not_empty:
                csv_writer.writeheader()

            for filename in sorted(os.listdir(OUTPUT_DIR)): # Ordenar para procesamiento predecible
                if filename.endswith(".csv") and "conversation_" in filename:
                    filepath = os.path.join(OUTPUT_DIR, filename)
                    if filename in evaluated_files:
                        print(f"La conversación {filename} ya ha sido evaluada. Omitiendo.")
                        continue

                    print(f"\nEvaluando: {filename}")
                    try:
                        conversation_df = pd.read_csv(filepath)

                        bot_llm_choice = 'N/A'
                        user_llm_choice = 'N/A'
                        
                        match_bot = re.search(r'_bot_([A-Za-z0-9]+)_', filename)
                        if match_bot:
                            bot_llm_choice = match_bot.group(1)
                            
                        match_user = re.search(r'_user_([A-Za-z0-9]+)_', filename)
                        if match_user:
                            user_llm_choice = match_user.group(1)

                        current_case = "caso_sebastian" if "sebastian" in filename.lower() else "caso_desconocido"
                        case_text = SEBASTIAN_CASE if current_case == "caso_sebastian" else "Caso desconocido (revisa config/generated_config.py)"
                        con_bot = "con_bot" in filename.lower() # Esto nos dice si hay un bot en la simulación

                        # --- Evaluación Holística (Siempre se ejecuta) ---
                        conversation_log_for_holistic_eval = ""
                        for _, row in conversation_df.iterrows():
                            timestamp_str = row.get('timestamp', 'N/A')
                            conversation_log_for_holistic_eval += f"[{timestamp_str}] {row['user_name']}: {row['message']}\n"
                        
                        holistic_eval_result = self.evaluate_conversation_holistic(conversation_log_for_holistic_eval, case_text)
                        print(f"  Evaluación General: {holistic_eval_result}")
                        time.sleep(WAIT_TIME) # Pausa después de la evaluación holística


                        # --- Preparación para la Evaluación de Intervenciones Específicas (Precision, Recall, F1, Calidad) ---
                        # Estas métricas SÓLO se calculan si la simulación incluyó un bot.
                        # Para las simulaciones sin bot, estas métricas se inicializarán a 0.
                        all_intervention_opportunities = []
                        messages_for_context = [] 

                        # Inicializar métricas de intervención. Serán 0 si no hay bot.
                        vp, fp, fn, vn = 0, 0, 0, 0
                        precision, recall, f1_score = 0, 0, 0
                        total_interventions = 0
                        avg_quality_clarity, avg_quality_relevance, avg_quality_depth = 0, 0, 0
                        avg_quality_adherence, avg_quality_role_compliance = 0, 0
                        avg_processing_time = 0

                        if con_bot: # <--- OPTIMIZACIÓN: Solo ejecutar esto si la simulación incluye un bot
                            for i, row in conversation_df.iterrows():
                                current_message = {
                                    "user_name": str(row['user_name']), 
                                    "message": str(row['message']),     
                                    "timestamp": row.get('timestamp', datetime.now().isoformat()) 
                                }
                                
                                context_for_eval = "\n".join([
                                    f"[{m['timestamp']}] {m['user_name']}: {m['message']}" for m in messages_for_context
                                ])
                                if not context_for_eval.strip(): 
                                    context_for_eval = "No hay historial previo."
                                
                                metadata = {}
                                if 'metadata' in row and pd.notna(row['metadata']):
                                    metadata_str = str(row['metadata']).strip()
                                    try:
                                        metadata = json.loads(metadata_str)
                                    except json.decoder.JSONDecodeError as e:
                                        print(f"      ADVERTENCIA: Fallo de parseo JSON para metadata. Error: {e}. Contenido problemático: '{metadata_str}'")
                                    except Exception as e:
                                        print(f"      ADVERTENCIA: Error inesperado al parsear metadata: {e}. Contenido problemático: '{metadata_str}'")

                                timing_info = {}
                                if 'timing_info' in row and pd.notna(row['timing_info']):
                                    timing_info_str = str(row['timing_info']).strip()
                                    try:
                                        timing_info = json.loads(timing_info_str)
                                    except json.decoder.JSONDecodeError as e:
                                        print(f"      ADVERTENCIA: Fallo de parseo JSON para timing_info. Error: {e}. Contenido problemático: '{timing_info_str}'")
                                    except Exception as e:
                                        print(f"      ADVERTENCIA: Error inesperado al parsear timing_info: {e}. Contenido problemático: '{timing_info_str}'")

                                # --- Caso: El mensaje actual es del BOT (Intervención Realizada) ---
                                if current_message['user_name'] == BOT_USERNAME:
                                    should_have_intervened_evaluator = False
                                    quality_scores = {
                                        "clarity_score": 0, "relevance_score": 0, "depth_score": 0,
                                        "adherence_score": 0, "role_compliance_score": 0
                                    }
                                    
                                    try:
                                        decision_eval = self.intervention_decision_chain.invoke({
                                            "context_history": context_for_eval,
                                            "bot_turn_content": current_message['message'] 
                                        })
                                        should_have_intervened_evaluator = decision_eval.get("should_have_intervened_evaluator", "NO").upper() == "SI"
                                        print(f"    Bot intervino: '{current_message['message'][:50]}...' -> Evaluador decisión: {'SÍ' if should_have_intervened_evaluator else 'NO'} debió. Razón: {decision_eval.get('rationale', 'N/A')}")
                                        time.sleep(WAIT_TIME)

                                        if should_have_intervened_evaluator: 
                                            supervisor_guidelines = metadata.get("supervisor_rationale", {}).get("intervention_guidelines", {})
                                            quality_eval = self.intervention_quality_chain.invoke({
                                                "context_history": context_for_eval, 
                                                "bot_intervention_text": current_message['message'],
                                                "bot_metadata_json": json.dumps(metadata),
                                                "supervisor_guidelines_json": json.dumps(supervisor_guidelines)
                                            })
                                            quality_scores = {
                                                "clarity_score": quality_eval.get("clarity_score", 0),
                                                "relevance_score": quality_eval.get("relevance_score", 0),
                                                "depth_score": quality_eval.get("depth_score", 0),
                                                "adherence_score": quality_eval.get("adherence_score", 0),
                                                "role_compliance_score": quality_eval.get("role_compliance_score", 0)
                                            }
                                            print(f"      Calidad: {quality_scores}")
                                        time.sleep(WAIT_TIME) 

                                    except OutputParserException as ope:
                                        print(f"      ADVERTENCIA: Fallo de parseo JSON para la intervención del bot. Error: {ope.llm_output}")
                                    except Exception as e:
                                        print(f"      ERROR inesperado al evaluar la intervención del bot: {e}")
                                        import traceback
                                        traceback.print_exc()
                                    
                                    all_intervention_opportunities.append({
                                        "bot_actual_intervened": True,
                                        "evaluator_ideal_intervene": should_have_intervened_evaluator,
                                        "processing_time": timing_info.get("total_llm_processing_time_seconds", 0),
                                        **quality_scores 
                                    })

                                # --- Caso: El mensaje actual es de USUARIO y el bot NO respondió en el SIGUIENTE turno (No-intervención) ---
                                elif current_message['user_name'] != BOT_USERNAME:
                                    is_last_message_of_conv = (i + 1 == len(conversation_df))
                                    bot_responded_next = (not is_last_message_of_conv and conversation_df.iloc[i+1]['user_name'] == BOT_USERNAME)

                                    if not bot_responded_next: # Esto significa que el bot NO intervino después de este mensaje de usuario
                                        try:
                                            decision_eval = self.intervention_decision_chain.invoke({
                                                "context_history": context_for_eval,
                                                "bot_turn_content": "No hubo intervención del bot." 
                                            })
                                            should_have_intervened_evaluator = decision_eval.get("should_have_intervened_evaluator", "NO").upper() == "SI"
                                            print(f"    Usuario: '{current_message['message'][:50]}...' -> Bot NO intervino. Evaluador decisión: {'SÍ' if should_have_intervened_evaluator else 'NO'} debió. Razón: {decision_eval.get('rationale', 'N/A')}")
                                            time.sleep(WAIT_TIME) 

                                            all_intervention_opportunities.append({
                                                "bot_actual_intervened": False,
                                                "evaluator_ideal_intervene": should_have_intervened_evaluator,
                                                "processing_time": 0 
                                            })
                                        except OutputParserException as ope:
                                            print(f"      ADVERTENCIA: Fallo de parseo JSON para la no-intervención. Error: {ope.llm_output}")
                                        except Exception as e:
                                            print(f"      ERROR inesperado al evaluar la no-intervención del bot: {e}")
                                            import traceback
                                            traceback.print_exc()
                                
                                # Añadir el mensaje actual al contexto para la *siguiente* iteración.
                                messages_for_context.append(current_message)
                                if len(messages_for_context) > 10: 
                                    messages_for_context.pop(0)

                            # --- Calcular métricas finales de intervención (solo si con_bot es True) ---
                            vp = sum(1 for d in all_intervention_opportunities if d["bot_actual_intervened"] and d["evaluator_ideal_intervene"])
                            fp = sum(1 for d in all_intervention_opportunities if d["bot_actual_intervened"] and not d["evaluator_ideal_intervene"])
                            fn = sum(1 for d in all_intervention_opportunities if not d["bot_actual_intervened"] and d["evaluator_ideal_intervene"])
                            vn = sum(1 for d in all_intervention_opportunities if not d["bot_actual_intervened"] and not d["evaluator_ideal_intervene"])

                            precision = vp / (vp + fp) if (vp + fp) > 0 else 0
                            recall = vp / (vp + fn) if (vp + fn) > 0 else 0
                            f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

                            total_interventions = vp + fp # Total de veces que el bot realmente intervino

                            # Calcular promedios de calidad (solo para VP)
                            quality_interventions = [d for d in all_intervention_opportunities if d["bot_actual_intervened"] and d["evaluator_ideal_intervene"]]
                            
                            avg_quality_clarity = sum(d.get("clarity_score", 0) for d in quality_interventions) / len(quality_interventions) if quality_interventions else 0
                            avg_quality_relevance = sum(d.get("relevance_score", 0) for d in quality_interventions) / len(quality_interventions) if quality_interventions else 0
                            avg_quality_depth = sum(d.get("depth_score", 0) for d in quality_interventions) / len(quality_interventions) if quality_interventions else 0
                            avg_quality_adherence = sum(d.get("adherence_score", 0) for d in quality_interventions) / len(quality_interventions) if quality_interventions else 0
                            avg_quality_role_compliance = sum(d.get("role_compliance_score", 0) for d in quality_interventions) / len(quality_interventions) if quality_interventions else 0
                            
                            avg_processing_time = sum(d["processing_time"] for d in all_intervention_opportunities if d["bot_actual_intervened"]) / total_interventions if total_interventions > 0 else 0

                        # Escribir los resultados en el archivo CSV
                        csv_writer.writerow({
                            "filename": filename,
                            "caso": current_case,
                            "bot_llm_choice": bot_llm_choice,
                            "user_llm_choice": user_llm_choice,
                            "con_bot": con_bot,
                            "coherencia_general": holistic_eval_result.get("coherencia_general"),
                            "tono_general": holistic_eval_result.get("tono_general"),
                            "pertinencia_general": holistic_eval_result.get("pertinencia_general"),
                            "reflexion_general": holistic_eval_result.get("reflexion_general"),
                            "total_interventions": total_interventions,
                            "vp_count": vp,
                            "fp_count": fp,
                            "fn_count": fn,
                            "vn_count": vn,
                            "precision": precision,
                            "recall": recall,
                            "f1_score": f1_score,
                            "avg_quality_clarity": avg_quality_clarity,
                            "avg_quality_relevance": avg_quality_relevance,
                            "avg_quality_depth": avg_quality_depth,
                            "avg_quality_adherence": avg_quality_adherence,
                            "avg_quality_role_compliance": avg_quality_role_compliance,
                            "avg_processing_time_seconds": avg_processing_time
                        })
                        evaluated_files.add(filename)

                    except Exception as e:
                        print(f"Error al leer o evaluar el archivo {filename}: {e}")
                        import traceback
                        traceback.print_exc()

        print(f"\n--- Evaluación de conversaciones finalizada. Los resultados se han guardado en: {evaluation_output_file} ---")

if __name__ == "__main__":
    evaluator = EvaluatorAgent(EVALUATOR_LLM_NAME)
    evaluator.evaluate_all_simulated_conversations()