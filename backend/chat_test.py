import json
import requests
import time
import random
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dotenv import load_dotenv
from threading import Event
import functools
import pandas as pd
import re

# Desactivar advertencias SSL si se usa verify=False (¡Solo para depuración!)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Importaciones de Langchain
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_deepseek import ChatDeepSeek
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable

# Cargar las variables de entorno desde .env
load_dotenv(override=True)

# --- CONFIGURACIÓN GLOBAL ---
API_BASE_URL = 'https://' + os.getenv("API_BASE_URL", "http://localhost:8000")

SIMULATION_INTERVAL_API = 10 # Pausa más larga para API para dar tiempo al bot
SIMULATION_INTERVAL_LOCAL = 2 # Pausa más corta para simulaciones sin bot
NUM_PARTICIPANTS = 3
TOTAL_TURNS = 15 * NUM_PARTICIPANTS # Número total de mensajes en una conversación
OUTPUT_DIR = "simulated_conversations"
DISABLE_SSL_VERIFICATION = os.getenv("DISABLE_SSL_VERIFICATION", "False").lower() == "true"

# --- Inicialización y Carga de Datos ---
os.makedirs(OUTPUT_DIR, exist_ok=True)
global_stop_event = Event()

if DISABLE_SSL_VERIFICATION:
    print("ADVERTENCIA: La verificación SSL está DESHABILITADA.")

# Carga de caso de estudio
try:
    from config.generated_config import SEBASTIAN_CASE
except ImportError:
    print("Advertencia: No se pudo importar SEBASTIAN_CASE. Usando texto por defecto.")
    SEBASTIAN_CASE = "Dilema ético sobre Sebastián."

# Decorador de reintentos (sin cambios, es sólido)
def retry_on_rate_limit(max_retries: int = 5, initial_delay: float = 2.0):
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            for i in range(max_retries):
                if global_stop_event.is_set(): raise InterruptedError("Operación interrumpida.")
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_msg = str(e).lower()
                    if "rate limit" in error_msg or "resource exhausted" in error_msg or "quota" in error_msg or "too many requests" in error_msg or (isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 429):
                        print(f"ATENCIÓN: Rate limit detectado en {func.__name__} (Intento {i+1}). Reintentando en {delay:.1f}s...")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        raise e
            raise Exception(f"{func.__name__} falló después de {max_retries} reintentos.")
        return wrapper
    return decorator

# --- Clases de Agentes y Gestión ---
class LLMAgent:
    """Agente para simular un participante con una personalidad definida."""
    def __init__(self, llm_name: str, api_key: str):
        self.llm_name = llm_name
        self.api_key = api_key
        self.llm = self._initialize_llm()
        self.output_parser = StrOutputParser()
        self.chains = {
            "conciliador": self._build_agent_chain("conciliador"),
            "esceptico": self._build_agent_chain("esceptico")
        }

    def _initialize_llm(self):
        config = {"temperature": 0.7, "max_tokens": 150, "request_timeout": 90}
        if self.llm_name == 'ChatGPT':
            return ChatOpenAI(model="gpt-4o-mini", api_key=self.api_key, **config)
        elif self.llm_name == 'Gemini':
            return ChatGoogleGenerativeAI(model="gemini-2.0-flash", api_key=self.api_key, **config)
        elif self.llm_name == 'DeepSeek':
            return ChatDeepSeek(model="deepseek-chat", api_key=self.api_key, **config)
        else:
            raise ValueError(f"Modelo no soportado: {self.llm_name}")

    def _build_agent_chain(self, personality: str) -> Runnable:
        instructions = ""
        if personality == "conciliador":
            instructions = "Tu único objetivo es BUSCAR EL ACUERDO Y REDUCIR EL CONFLICTO. Siempre que alguien proponga una idea, muéstrate de acuerdo, refuérzala con un comentario simple, o intenta encontrar un punto medio. Evita la confrontación."
        elif personality == "esceptico":
            instructions = "Tu único objetivo es CUESTIONAR LAS AFIRMACIONES de los demás de forma simple. No ofrezcas contraargumentos complejos. Simplemente pregunta '¿por qué?', '¿estás seguro de eso?', o 'no lo veo tan claro'."
        
        template_str = (
            f"Eres un participante en un debate ético. {instructions}\n"
            "**REGLAS CRÍTICAS:**\n"
            "- Tu respuesta debe ser un ÚNICO MENSAJE DE CHAT CORTO (10-30 palabras).\n"
            "- Relaciónate con el historial reciente, pero no repitas frases.\n"
            "- Responde SOLO con el mensaje. No incluyas NADA MÁS (ni metadatos, ni justificaciones, ni tu rol).\n\n"
            "--- CASO ---\n{case}\n\n"
            "--- HISTORIAL DE CONVERSACIÓN ---\n{conversation_history}\n\n"
            "--- TU TURNO ---\nAhora, genera tu mensaje como {participant_name}:"
        )
        return ChatPromptTemplate.from_template(template_str) | self.llm | self.output_parser

    @retry_on_rate_limit()
    def generate_message(self, participant_name: str, conversation_history: List[Dict], case: str, personality: str) -> str:
        chain = self.chains[personality]
        formatted_history = "\n".join([f"{msg.get('user_name', 'User')}: {msg.get('message', '')}" for msg in conversation_history[-5:]]) # Solo los últimos 5 mensajes
        response = chain.invoke({
            "participant_name": participant_name,
            "conversation_history": formatted_history,
            "case": case,
        })
        return response.strip().replace('"', '')

class RoomManager:
    """Gestiona la comunicación con la API del backend."""
    def __init__(self, api_base_url: str):
        self.base_url = api_base_url.replace('/api', '') # Asegurarse de tener la URL base

    def create_room(self) -> Optional[str]:
        try:
            response = requests.post(f"{self.base_url}/api/create_room", verify=not DISABLE_SSL_VERIFICATION)
            response.raise_for_status()
            return response.json().get("room_id")
        except requests.exceptions.RequestException as e:
            print(f"Error al crear sala: {e}")
            return None

    @retry_on_rate_limit()
    def send_message(self, room_id: str, username: str, message: str, llm_choice_for_bot: str):
        data = {"room_id": room_id, "user_name": username, "message": message, "llm_choice_for_bot": llm_choice_for_bot}
        response = requests.post(f"{self.base_url}/api/simulate_message", json=data, verify=not DISABLE_SSL_VERIFICATION)
        response.raise_for_status()

    def get_recent_messages(self, room_id: str, limit: int = 50) -> List[Dict]:
        try:
            response = requests.get(f"{self.base_url}/api/chat/{room_id}", verify=not DISABLE_SSL_VERIFICATION)
            response.raise_for_status()
            return response.json().get("messages", [])
        except requests.exceptions.RequestException:
            return []

class Simulation:
    """Ejecuta una única simulación de conversación."""
    def __init__(self, room_manager: RoomManager, config: Dict, case_text: str, api_key: str, stop_event: Event):
        self.room_manager = room_manager
        self.config = config
        self.case_text = case_text
        self.api_key = api_key
        self.stop_event = stop_event
        self.conversation_history = []
        self.agent = LLMAgent(config['user_llm'], api_key)

    def run(self):
        """Ejecuta la simulación completa."""
        room_id = "no_api_" + self.config['simulation_id']
        if self.config['use_bot']:
            created_room_id = self.room_manager.create_room()
            if not created_room_id:
                print(f"ERROR: Fallo crítico al crear sala para {self.config['simulation_id']}. Abortando.")
                return
            room_id = created_room_id
        
        print(f"Iniciando simulación ID: {self.config['simulation_id']}, Sala: {room_id}")
        
        participants = [f"SimAgent_{i+1}_{self.config['user_llm']}" for i in range(NUM_PARTICIPANTS)]
        
        for turn in range(TOTAL_TURNS):
            if self.stop_event.is_set():
                print(f"Simulación {self.config['simulation_id']} abortada.")
                break
                
            participant_to_speak = random.choice(participants)
            
            try:
                message = self.agent.generate_message(
                    participant_name=participant_to_speak,
                    conversation_history=self.conversation_history,
                    case=self.case_text,
                    personality=self.config['user_personality']
                )
                print(f"  [Turno {turn+1}/{TOTAL_TURNS}] {participant_to_speak}: {message}")

                if self.config['use_bot']:
                    self.room_manager.send_message(room_id, participant_to_speak, message, self.config['bot_llm'])
                    time.sleep(SIMULATION_INTERVAL_API)
                    self.conversation_history = self.room_manager.get_recent_messages(room_id)
                else:
                    self.conversation_history.append({"user_name": participant_to_speak, "message": message, "timestamp": datetime.now().isoformat()})
                    time.sleep(SIMULATION_INTERVAL_LOCAL)
            except Exception as e:
                print(f"ERROR en turno {turn+1} de simulación {self.config['simulation_id']}: {e}")
                break
        
        self._export_to_csv()

    def _export_to_csv(self):
        """Exporta el historial de la conversación a un archivo CSV, procesando timing_info."""
        if not self.conversation_history:
            print(f"Simulación {self.config['simulation_id']} no generó datos para exportar.")
            return

        # Extraer y aplanar la información de tiempo
        processed_history = []
        for msg in self.conversation_history:
            # Hacemos una copia para no modificar el original
            new_msg = msg.copy()
            
            # Extraemos el tiempo de procesamiento si el mensaje es del bot
            if new_msg.get('user_name') == 'Bot' and 'timing_info' in new_msg and isinstance(new_msg['timing_info'], dict):
                # Añadimos una nueva columna con el tiempo de procesamiento
                new_msg['processing_time_s'] = new_msg['timing_info'].get('total_llm_processing_time_seconds', None)
            else:
                new_msg['processing_time_s'] = None # O np.nan si prefieres
            
            # Limpiamos las columnas que no necesitamos para un CSV limpio
            # Esto es opcional, pero hace el CSV más legible
            keys_to_keep = ['timestamp', 'user_name', 'message', 'processing_time_s']
            final_msg = {key: new_msg.get(key) for key in keys_to_keep}
            processed_history.append(final_msg)

        df = pd.DataFrame(processed_history)

        filename = os.path.join(OUTPUT_DIR, f"conversation_{self.config['simulation_id']}.csv")
        df.to_csv(filename, index=False, encoding='utf-8', float_format='%.4f')
        print(f"Conversación {self.config['simulation_id']} exportada a: {filename}")


# --- FUNCIÓN PRINCIPAL ---
def run_main_simulation():
    all_api_keys = {
        "ChatGPT": os.getenv("OPENAI_API_KEY"),
        "Gemini": os.getenv("GOOGLE_API_KEY"),
        "DeepSeek": os.getenv("DEEPSEEK_API_KEY"),
    }
    print("API Keys Cargadas:")
    for llm, key in all_api_keys.items():
        print(f"  {llm}: {'Configurada' if key else 'NO CONFIGURADA'}")

    room_manager = RoomManager(API_BASE_URL)

    # --- Matriz de Experimentos Completa y Segura ---
    experiment_matrix = [
        # === Escenario CONVERGENTE ===
        {"scenario": "convergente", "use_bot": True,  "bot_llm": "ChatGPT",  "user_llm": "ChatGPT", "user_personality": "conciliador"},
        {"scenario": "convergente", "use_bot": True,  "bot_llm": "Gemini",   "user_llm": "Gemini",  "user_personality": "conciliador"},
        {"scenario": "convergente", "use_bot": True,  "bot_llm": "DeepSeek", "user_llm": "DeepSeek", "user_personality": "conciliador"},
        {"scenario": "convergente", "use_bot": False, "bot_llm": "NA", "user_llm": "ChatGPT",  "user_personality": "conciliador"},
        {"scenario": "convergente", "use_bot": False, "bot_llm": "NA", "user_llm": "Gemini",   "user_personality": "conciliador"},
        {"scenario": "convergente", "use_bot": False, "bot_llm": "NA", "user_llm": "DeepSeek", "user_personality": "conciliador"},
        # === Escenario DIVERGENTE ===
        {"scenario": "divergente",  "use_bot": True,  "bot_llm": "ChatGPT",  "user_llm": "ChatGPT", "user_personality": "esceptico"},
        {"scenario": "divergente",  "use_bot": True,  "bot_llm": "Gemini",   "user_llm": "Gemini",  "user_personality": "esceptico"},
        {"scenario": "divergente",  "use_bot": True,  "bot_llm": "DeepSeek", "user_llm": "DeepSeek", "user_personality": "esceptico"},
        {"scenario": "divergente",  "use_bot": False, "bot_llm": "NA", "user_llm": "ChatGPT",  "user_personality": "esceptico"},
        {"scenario": "divergente",  "use_bot": False, "bot_llm": "NA", "user_llm": "Gemini",   "user_personality": "esceptico"},
        {"scenario": "divergente",  "use_bot": False, "bot_llm": "NA", "user_llm": "DeepSeek", "user_personality": "esceptico"},
    ]
    REPETITIONS = 10 

    print("\n--- Iniciando/Reanudando el Banco de Pruebas Sintético ---")
    timestamp_prefix = datetime.now().strftime("%Y%m%d")
    
    # Calcular el total de simulaciones para mostrar el progreso
    total_sims_to_run = len(experiment_matrix) * REPETITIONS
    completed_sims = 0

    for exp_config in experiment_matrix:
        for i in range(REPETITIONS):
            if global_stop_event.is_set():
                print("Abortando ejecución por señal de parada.")
                return

            # Construir el nombre de archivo de salida esperado
            sim_id = f"{timestamp_prefix}_{exp_config['scenario']}_pers-{exp_config['user_personality']}_" \
                     f"cond-{'bot' if exp_config['use_bot'] else 'ctrl'}_bot-{exp_config['bot_llm'].lower()}_" \
                     f"user-{exp_config['user_llm'].lower()}_rep-{i+1}"
            
            output_filename = os.path.join(OUTPUT_DIR, f"conversation_{sim_id}.csv")

            # --- LA MEJORA ANTI-PSICOSIS ---
            # Comprobar si la simulación ya ha sido completada
            if os.path.exists(output_filename):
                print(f"({completed_sims+1}/{total_sims_to_run}) SIMULACIÓN YA EXISTE: {os.path.basename(output_filename)}. Saltando.")
                completed_sims += 1
                continue

            print(f"\n({completed_sims+1}/{total_sims_to_run}) INICIANDO: {sim_id}")
            
            # Añadir el ID a la configuración de esta simulación
            current_sim_config = exp_config.copy()
            current_sim_config['simulation_id'] = sim_id

            api_key_for_user = all_api_keys.get(exp_config['user_llm'])
            if not api_key_for_user:
                print(f"ADVERTENCIA: No hay API key para {exp_config['user_llm']}. Saltando.")
                continue

            simulation = Simulation(
                room_manager=room_manager,
                config=current_sim_config,
                case_text=SEBASTIAN_CASE,
                api_key=api_key_for_user,
                stop_event=global_stop_event
            )
            simulation.run()
            completed_sims += 1
            
            if not global_stop_event.is_set():
                time.sleep(random.uniform(5, 10)) # Pausa para no saturar APIs

    print(f"\n--- Banco de Pruebas Finalizado. Total de simulaciones verificadas/ejecutadas: {completed_sims} ---")

if __name__ == "__main__":
    try:
        run_main_simulation()
    except KeyboardInterrupt:
        print("\nSe detectó CTRL+C. Señalando para terminar de forma limpia...")
        global_stop_event.set()
    finally:
        print("\n--- Script finalizado. ---")