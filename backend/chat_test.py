import json
import requests
import time
import random
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dotenv import load_dotenv
# Eliminado: from threading import Thread
from threading import Event # Se mantiene Event para global_stop_event
import functools
import ast # <--- AÑADIDO: Importar el módulo 'ast'

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

import pandas as pd
import re # Asegurar la importación de 're'

# Cargar las variables de entorno desde .env
load_dotenv(override=True)

# --- Configuración Global y Carga de Datos ---
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000") 
# Ajuste CRÍTICO: Asegurarse de que API_BASE_URL en .env NO contenga "https://"
# Si API_BASE_URL ya es "https://host...", entonces la siguiente línea sería:
# API_URL_PREFIX = f"{API_BASE_URL}/api"
# Pero asumiendo que API_BASE_URL es solo "host:port" o "host", la siguiente línea es correcta:
API_URL_PREFIX = f"https://{API_BASE_URL}/api" 

SIMULATION_INTERVAL = 5 # Intervalo aumentado para simulación secuencial
USER_MESSAGES_CSV = ".data_usr_msg.csv"
OUTPUT_DIR = "simulated_conversations"

DISABLE_SSL_VERIFICATION = os.getenv("DISABLE_SSL_VERIFICATION", "False").lower() == "true"
if DISABLE_SSL_VERIFICATION:
    print("ADVERTENCIA: La verificación SSL está DESHABILITADA. Esto NO es seguro para producción.")

os.makedirs(OUTPUT_DIR, exist_ok=True)

_SEBASTIAN_CASE_DEFAULT = "Este es un caso de ejemplo por defecto sobre un dilema ético con Sebastián. El caso real no pudo ser cargado."
try:
    from config.generated_config import SEBASTIAN_CASE
except ImportError:
    print("Advertencia: No se pudo importar SEBASTIAN_CASE de config.generated_config. Usando texto por defecto.")
    SEBASTIAN_CASE = _SEBASTIAN_CASE_DEFAULT

def load_user_messages(csv_path: str) -> pd.DataFrame:
    """Carga los mensajes de usuario desde un archivo CSV de forma robusta."""
    try:
        df = pd.read_csv(csv_path)
        if 'user_id' not in df.columns or 'message' not in df.columns:
            print(f"Advertencia: El archivo CSV '{csv_path}' no contiene las columnas 'user_id' y 'message'.")
            return pd.DataFrame(columns=['user_id', 'message'])
        
        # AÑADIDO: Limpieza básica de los mensajes de ejemplo
        # Esto es crucial para evitar que el LLM aprenda a incluir metadatos de los ejemplos.
        df['message'] = df['message'].astype(str) # Asegurar que es string
        df['message'] = df['message'].apply(lambda x: x.split('(alternativa')[0].strip() if '(alternativa' in x else x)
        df['message'] = df['message'].apply(lambda x: x.split('(Claves logradas:')[0].strip() if '(Claves logradas:' in x else x)
        df['message'] = df['message'].apply(lambda x: x.split('(O más corto:')[0].strip() if '(O más corto:' in x else x) # Para el patrón de tus ejemplos
        df['message'] = df['message'].apply(lambda x: x.split('(Opcional:')[0].strip() if '(Opcional:' in x else x)
        df['message'] = df['message'].apply(lambda x: x.split('(¿Quieres ajustar el tono?')[0].strip() if '(¿Quieres ajustar el tono?' in x else x)
        df['message'] = df['message'].apply(lambda x: x.split('(Mensaje típico:')[0].strip() if '(Mensaje típico:' in x else x) # Nuevo para tus ejemplos
        df['message'] = df['message'].apply(lambda x: x.strip()) # Limpiar espacios extra
        df = df[df['message'].str.len() > 10] # Eliminar mensajes muy cortos después de la limpieza
        df = df[df['message'].str.contains(r'[a-zA-Z0-9]', na=False)] # Eliminar filas solo con emojis o vacías

        return df
    except FileNotFoundError:
        print(f"Error: El archivo CSV '{csv_path}' no fue encontrado. Asegúrate de que existe.")
        return pd.DataFrame(columns=['user_id', 'message'])
    except pd.errors.EmptyDataError:
        print(f"Advertencia: El archivo CSV '{csv_path}' está vacío.")
        return pd.DataFrame(columns=['user_id', 'message'])
    except Exception as e:
        print(f"Error inesperado al leer el archivo CSV '{csv_path}': {e}")
        return pd.DataFrame(columns=['user_id', 'message'])

# Carga global del DataFrame de mensajes de usuario (se carga una sola vez)
base_dir = os.path.dirname(os.path.abspath(__file__))
historical_messages_csv_path = os.path.join(base_dir, USER_MESSAGES_CSV)
user_messages_df = load_user_messages(historical_messages_csv_path)

if user_messages_df.empty and USER_MESSAGES_CSV:
    print("No se pudieron cargar mensajes de usuario. Las respuestas del LLM podrían ser menos realistas.")

global_stop_event = Event()

def retry_on_rate_limit(max_retries: int = 5, initial_delay: float = 1.0):
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            for i in range(max_retries):
                if global_stop_event.is_set():
                    print(f"DEBUG: {func.__name__} abortado por stop_event durante reintento {i+1}.")
                    raise InterruptedError("Operación interrumpida por señal de parada.")

                try:
                    return func(*args, **kwargs)
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:
                        print(f"ATENCIÓN: Rate limit HTTP 429 en {func.__name__} (Intento {i+1}/{max_retries}). Reintentando en {delay:.2f}s...")
                        time.sleep(delay) # Modificado: global_stop_event.wait(delay) -> time.sleep(delay)
                        delay *= 2
                    else:
                        print(f"ERROR: Fallo HTTP no 429 en {func.__name__} (Intento {i+1}/{max_retries}): {e}")
                        raise e
                except requests.exceptions.ConnectionError as e:
                    print(f"ATENCIÓN: Error de conexión/SSL en {func.__name__} (Intento {i+1}/{max_retries}): {e}. Reintentando en {delay:.2f}s...")
                    time.sleep(delay) # Modificado: global_stop_event.wait(delay) -> time.sleep(delay)
                    delay *= 2
                except Exception as e:
                    error_msg = str(e).lower()
                    if "rate limit" in error_msg or "resource exhausted" in error_msg or "quota" in error_msg or "too many requests" in error_msg:
                        print(f"ATENCIÓN: Error de API (posible rate limit/cuota) en {func.__name__} (Intento {i+1}/{max_retries}): {e}. Reintentando en {delay:.2f}s...")
                        time.sleep(delay) # Modificado: global_stop_event.wait(delay) -> time.sleep(delay)
                        delay *= 2
                    else:
                        print(f"ERROR: Fallo no relacionado con rate limit en {func.__name__} (Intento {i+1}/{max_retries}): {e}. No reintentando para este tipo de error.")
                        raise e 

            print(f"ERROR FATAL: {func.__name__} falló después de {max_retries} reintentos.")
            raise requests.exceptions.RequestException(f"Falló después de {max_retries} reintentos debido a rate limits o errores de API.")
        return wrapper
    return decorator

class LLMAgent:
    """Agente base para generar mensajes con un LLM imitando usuarios reales de EthicApp."""

    def __init__(self, llm_name: str, api_key: str):
        self.llm_name = llm_name
        self.api_key = api_key
        self.llm = self.initialize_llm()
        self.output_parser = StrOutputParser()
        self.chains = {
            "typical": self.build_typical_user_chain()
        }

    def initialize_llm(self):
        """Inicializa el modelo de lenguaje adecuado con un timeout para las solicitudes."""
        LLM_REQUEST_TIMEOUT = 90 # segundos
        request_config = {"request_timeout": LLM_REQUEST_TIMEOUT}
        if DISABLE_SSL_VERIFICATION:
            request_config['verify_ssl'] = False 

        llm_temperature = 0.7 
        llm_max_tokens = 150 # Limita la longitud de la respuesta, ~50-100 palabras

        if self.llm_name == 'ChatGPT':
            if not self.api_key:
                raise ValueError(f"API Key (OPENAI_API_KEY) no proporcionada para {self.llm_name}.")
            return ChatOpenAI(model="gpt-4o-mini", temperature=llm_temperature, api_key=self.api_key, max_tokens=llm_max_tokens, **request_config)
        elif self.llm_name == 'Gemini':
            if not self.api_key:
                raise ValueError(f"API Key (GOOGLE_API_KEY) no proporcionada para {self.llm_name}.")
            return ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=llm_temperature, api_key=self.api_key, max_tokens=llm_max_tokens, **request_config)
        elif self.llm_name == 'DeepSeek':
            if not self.api_key:
                raise ValueError(f"API Key (DEEPSEEK_API_KEY) no proporcionada para {self.llm_name}.")
            return ChatDeepSeek(model="deepseek-chat", temperature=llm_temperature, api_key=self.api_key, max_tokens=llm_max_tokens, **request_config)
        else:
            raise ValueError(f"Modelo de lenguaje no soportado: {self.llm_name}. Opciones válidas: 'ChatGPT', 'Gemini', 'DeepSeek'.")


    def build_typical_user_chain(self) -> Runnable:
        """Construye la cadena para generar mensajes como un usuario típico de EthicApp."""
        prompt = ChatPromptTemplate.from_messages([
            HumanMessagePromptTemplate.from_template(
                """Eres {participant_name}, un estudiante universitario típico participando en un debate ético sobre el caso.

                Tu objetivo es generar **UN ÚNICO MENSAJE DE USUARIO CORTO** (entre 3 y 6 oraciones, máximo 100 palabras).
                El mensaje debe reflejar la forma en que los estudiantes chilenos se expresan en línea, con:
                - Lenguaje coloquial, jerga juvenil, y uso de abreviaciones o errores leves (ej. "noma", "po", "onda", "cacho", "wsp", "tbn").
                - Uso frecuente de emojis o emoticones (ej. 😂😭😅😬👍🤙✨👀).
                - Un tono que puede variar entre despreocupado, emocional, pragmático o ligeramente irónico.
                - Comentarios breves sobre el caso, reacciones iniciales, o expresiones de opiniones sin profundizar en el razonamiento ético o presentar contraargumentos detallados.
                - El contenido debe estar relacionado con el último turno o el caso general, pero **sin repetir frases exactas** de mensajes anteriores o del caso.
                - **ES CRÍTICO**: Tu respuesta debe ser *SOLO el mensaje del usuario*. No incluyas NINGÚN tipo de metadato, instrucción, justificación, alternativas, claves logradas, texto entre paréntesis o cualquier otro comentario adicional. Empieza y termina directamente con el mensaje.

                --- EJEMPLOS DE MENSAJES REALES DE USUARIOS DE ETHICAPP ---
                {user_messages}
                --- FIN DE EJEMPLOS ---

                Considera el siguiente caso:
                {case}

                Este es el historial de conversación reciente:
                {conversation_history}

                Ahora, genera tu mensaje siguiendo estrictamente las instrucciones:
                """
            )
        ])
        return prompt | self.llm | self.output_parser

    @retry_on_rate_limit(max_retries=5, initial_delay=2.0)
    def generate_message(self, participant_name: str, conversation_history: List[Dict], case: str, user_messages: str, conversation_type: str = "typical") -> str:
        """Genera un mensaje como un usuario típico."""
        if conversation_type not in self.chains:
            raise ValueError(f"Tipo de conversación no soportado: {conversation_type}")

        chain = self.chains[conversation_type]
        response = chain.invoke({
            "participant_name": participant_name,
            "conversation_history": conversation_history,
            "case": case,
            "user_messages": user_messages,
        })
        
        # AÑADIDO: Limpieza post-generación para asegurar que no hay metadatos.
        # Esto es un respaldo si el prompt no es 100% efectivo.
        response_cleaned = response.strip()
        # Patrones comunes que los LLMs pueden "pegar" del prompt o de su entrenamiento
        patterns_to_remove = [
            r'\s*\(.*\)\s*$', # Eliminar paréntesis al final (ej. (alternativa...), (Claves logradas:))
            r'^\s*alternativa:?\s*',
            r'^\s*o más cort(o|ita|ito):?\s*',
            r'^\s*claves logradas:?\s*',
            r'^\s*\[?mensaje típico\]?:?\s*',
            r'^\s*\[?opcional\]?:?\s*',
            r'^\s*qué valores entran en conflicto aquí:?\s*', # Del bot de ejemplo
            r'^\s*genera tu mensaje:?\s*',
            r'^\s*alternativa más desestructurada:?\s*',
            r'^\s*alternativa más exagerada:?\s*',
            r'^\s*opcional: agregar sticker.*$',
            r'^\s*\*\*(Claves logradas|Mensaje típico|Alternativa|Opcional|Qué valores).*$', # Más general
            r'^\s*O más corto:.*$', # Eliminar línea completa si comienza con "O más corto:"
            r'^\s*\(Opcional:.*$', # Eliminar línea completa si comienza con "(Opcional:"
        ]
        
        for pattern in patterns_to_remove:
            response_cleaned = re.sub(pattern, '', response_cleaned, flags=re.IGNORECASE | re.MULTILINE).strip()

        # Asegurar que el mensaje no esté vacío o solo espacios/emojis
        if len(response_cleaned) < 5 and any(char.isalpha() for char in response_cleaned):
             # Si es muy corto pero tiene letras, puede ser válido
             pass
        elif len(response_cleaned) < 5: # Si es muy corto y no tiene letras, puede ser solo emojis o ruido
            return "No se pudo generar un mensaje válido. (Error de generación)" # Mensaje de fallback
        
        return response_cleaned


class RoomManager:
    """Clase para gestionar las salas de chat."""

    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url

    def create_room(self) -> Optional[str]:
        """Crea una nueva sala de chat."""
        try:
            response = requests.post(f"{self.api_base_url}/create_room", verify=not DISABLE_SSL_VERIFICATION)
            response.raise_for_status()
            return response.json().get("room_id")
        except requests.exceptions.RequestException as e:
            print(f"Error al crear la sala: {e}")
            raise

    def set_username(self, room_id: str, username: str) -> Optional[requests.cookies.RequestsCookieJar]:
        """Establece un nombre de usuario para la sesión."""
        try:
            session = requests.Session()
            response = session.post(f"{self.api_base_url}/set_username", json={"username": username}, verify=not DISABLE_SSL_VERIFICATION)
            response.raise_for_status()
            return session.cookies
        except requests.exceptions.RequestException as e:
            print(f"Error al establecer el nombre de usuario {username} para la sala {room_id}: {e}")
            raise

    @retry_on_rate_limit(max_retries=5, initial_delay=2.0)
    def send_message(self, room_id: str, username: str, message: str, llm_choice_for_bot: str, cookies: Optional[requests.cookies.RequestsCookieJar] = None) -> bool:
        """Envía un mensaje simulado."""
        headers = {"Content-Type": "application/json"}
        url = f"{self.api_base_url}/simulate_message"
        data = {"room_id": room_id, "user_name": username, "message": message, "llm_choice_for_bot": llm_choice_for_bot}
        
        if cookies:
            response = requests.post(url, headers=headers, json=data, cookies=cookies, verify=not DISABLE_SSL_VERIFICATION)
        else:
            response = requests.post(url, headers=headers, json=data, verify=not DISABLE_SSL_VERIFICATION)
        response.raise_for_status()
        return True

    def get_recent_messages(self, room_id: str, limit: int = 50) -> List[Dict]:
        """Obtiene los mensajes recientes de la sala."""
        try:
            response = requests.get(f"{self.api_base_url}/chat/{room_id}", verify=not DISABLE_SSL_VERIFICATION)
            response.raise_for_status()
            messages = response.json().get("messages", [])
            return messages[-limit:]
        except requests.exceptions.RequestException as e:
            print(f"Error al obtener mensajes recientes para la sala {room_id}: {e}")
            return None


class Simulation:
    """Clase para gestionar la simulación de conversaciones y exportarlas a CSV."""

    def __init__(self, room_manager: RoomManager, bot_llm_choice: str, user_llm_choice: str, user_api_key: str, num_participants: int, case: str, num_messages_per_participant: int = 5, conversation_type: str = "typical", simulation_id: str = None, use_bot: bool = True, user_messages_df: pd.DataFrame = None, stop_event: Event = None):
        self.room_manager = room_manager
        self.bot_llm_choice = bot_llm_choice
        self.user_llm_choice = user_llm_choice
        self.agent = LLMAgent(user_llm_choice, user_api_key)
        self.num_participants = num_participants
        self.num_messages_per_participant = num_messages_per_participant
        self.conversation_type = conversation_type
        self.case = case
        self.conversation_history = []
        self.simulation_id = simulation_id if simulation_id else datetime.now().strftime("%Y%m%d_%H%M%S")
        self.use_bot = use_bot
        self.user_messages_df = user_messages_df if user_messages_df is not None else pd.DataFrame()
        self.stop_event = stop_event if stop_event is not None else Event()

    def simulate(self):
        """Simula una conversación y guarda el historial en un CSV."""
        if self.stop_event.is_set():
            print(f"[{self.bot_llm_choice}/{self.user_llm_choice}] Simulación {self.simulation_id} abortada antes de iniciar.")
            return

        room_id = None
        if self.use_bot:
            try:
                room_id = self.room_manager.create_room()
            except Exception as e:
                print(f"ERROR: Fallo crítico al crear la sala para simulación {self.simulation_id}: {e}. Abortando.")
                return
        else:
            room_id = "no_api_" + self.simulation_id

        if not room_id and self.use_bot:
            print(f"No se pudo crear la sala para la simulación {self.simulation_id} (Bot: {self.bot_llm_choice}, User: {self.user_llm_choice}). Saltando.")
            return

        simulation_type_str = "con_bot" if self.use_bot else "sin_bot"
        print(f"[Bot: {self.bot_llm_choice}, User: {self.user_llm_choice}] Iniciando simulación ID: {self.simulation_id}, Tipo: {simulation_type_str}, Sala: {room_id}")

        participants = [f"SimAgent_{i+1}_{self.user_llm_choice}" for i in range(self.num_participants)]
        participant_sessions = {}
        messages_sent_by_user = [0] * self.num_participants

        sample_messages_list = self.user_messages_df['message'].tolist() if not self.user_messages_df.empty else []

        if self.use_bot:
            for participant in participants:
                if self.stop_event.is_set():
                    print(f"[{self.bot_llm_choice}/{self.user_llm_choice}] Simulación {self.simulation_id} abortada durante unión de participantes.")
                    return

                try:
                    cookies = self.room_manager.set_username(room_id, participant)
                    if cookies:
                        participant_sessions[participant] = cookies
                        print(f"[Bot: {self.bot_llm_choice}, User: {self.user_llm_choice}] {participant} se unió a la sala {room_id}.")
                        time.sleep(0.5) # Modificado: stop_event.wait(0.5) -> time.sleep(0.5)
                    else:
                        print(f"[Bot: {self.bot_llm_choice}, User: {self.user_llm_choice}] No se pudo establecer nombre de usuario para {participant}. Esta simulación podría ser inestable.")
                except Exception as e:
                    print(f"ERROR: Fallo al establecer nombre de usuario para {participant}: {e}. Abortando simulación {self.simulation_id}.")
                    return

            total_user_messages = self.num_messages_per_participant * self.num_participants
            user_messages_count = 0

            participants_to_send_from = list(range(self.num_participants))

            while user_messages_count < total_user_messages and participants_to_send_from and not self.stop_event.is_set():
                participant_index = random.choice(participants_to_send_from)
                participant = participants[participant_index]

                if self.stop_event.is_set():
                    print(f"DEBUG: {self.bot_llm_choice}/{self.user_llm_choice} - Detención solicitada antes de get_recent_messages.")
                    break

                recent_messages = self.room_manager.get_recent_messages(room_id)
                if recent_messages is None:
                    if self.stop_event.is_set():
                        print(f"DEBUG: {self.bot_llm_choice}/{self.user_llm_choice} - Fallo en get_recent_messages y detención solicitada.")
                        break
                    else:
                        print(f"ADVERTENCIA: Fallo al obtener mensajes recientes para la sala {room_id}. Continuando con historial vacío.")
                        recent_messages = []

                current_user_messages_sample = ' '.join(random.sample(sample_messages_list, min(len(sample_messages_list), 500))) if sample_messages_list else "No hay ejemplos de mensajes de usuario."

                try:
                    if self.stop_event.is_set():
                        print(f"DEBUG: {self.bot_llm_choice}/{self.user_llm_choice} - Detención solicitada antes de generate_message.")
                        break
                    simulated_message = self.agent.generate_message(participant, recent_messages, self.case, current_user_messages_sample, self.conversation_type)
                    
                    if self.stop_event.is_set():
                        print(f"DEBUG: {self.bot_llm_choice}/{self.user_llm_choice} - Detención solicitada antes de send_message.")
                        break
                    cookies = participant_sessions.get(participant)
                    if self.room_manager.send_message(room_id, participant, simulated_message, llm_choice_for_bot=self.bot_llm_choice, cookies=cookies):
                        print(f"[Bot: {self.bot_llm_choice}, User: {self.user_llm_choice}] {participant}: {simulated_message}")
                        user_messages_count += 1
                        messages_sent_by_user[participant_index] += 1
                        if messages_sent_by_user[participant_index] >= self.num_messages_per_participant:
                            participants_to_send_from.remove(participant_index)
                        time.sleep(random.uniform(SIMULATION_INTERVAL * 0.5, SIMULATION_INTERVAL * 2)) # Modificado
                        time.sleep(1) # Modificado

                    if self.stop_event.is_set():
                        print(f"DEBUG: {self.bot_llm_choice}/{self.user_llm_choice} - Detención solicitada después de enviar mensaje.")
                        break

                    all_messages = self.room_manager.get_recent_messages(room_id, limit=1000)
                    if all_messages is None:
                        if self.stop_event.is_set():
                            print(f"DEBUG: {self.bot_llm_choice}/{self.user_llm_choice} - Fallo en get_recent_messages (final) y detención solicitada.")
                            break
                        else:
                            print(f"ADVERTENCIA: Fallo al obtener mensajes recientes para la sala {room_id} (final).")
                            all_messages = []

                    current_history_messages_set = {json.dumps(msg, sort_keys=True) for msg in self.conversation_history}
                    
                    # --- INICIO DE MODIFICACIÓN: Procesar mensajes de la API para uniformar campos ---
                    processed_api_messages = []
                    for msg in all_messages:
                        # Procesar 'metadata'
                        if 'metadata' in msg and isinstance(msg['metadata'], str):
                            try:
                                msg['metadata'] = json.loads(msg['metadata'])
                            except json.JSONDecodeError:
                                # Si falla el parseo JSON, intentar con ast.literal_eval para strings con comillas simples
                                try:
                                    msg['metadata'] = ast.literal_eval(msg['metadata'])
                                except (ValueError, SyntaxError):
                                    msg['metadata'] = {} # Por defecto, un diccionario vacío si no se puede parsear
                                    print(f"      ADVERTENCIA: Fallo al parsear string de metadata de la API: '{msg['metadata']}'. Usando diccionario vacío.")
                        elif 'metadata' not in msg or msg['metadata'] is None:
                            msg['metadata'] = {} # Asegurar que sea un diccionario incluso si falta o es None

                        # Procesar 'timing_info'
                        if 'timing_info' in msg and isinstance(msg['timing_info'], str):
                            try:
                                msg['timing_info'] = json.loads(msg['timing_info'])
                            except json.JSONDecodeError:
                                # Si falla el parseo JSON, intentar con ast.literal_eval para strings con comillas simples
                                try:
                                    msg['timing_info'] = ast.literal_eval(msg['timing_info'])
                                except (ValueError, SyntaxError):
                                    msg['timing_info'] = {} # Por defecto, un diccionario vacío si no se puede parsear
                                    print(f"      ADVERTENCIA: Fallo al parsear string de timing_info de la API: '{msg['timing_info']}'. Usando diccionario vacío.")
                        elif 'timing_info' not in msg or msg['timing_info'] is None:
                            msg['timing_info'] = {} # Asegurar que sea un diccionario incluso si falta o es None
                        
                        processed_api_messages.append(msg)

                    # Ahora, añadir los mensajes procesados al historial de conversación
                    for msg in processed_api_messages: # Usar los mensajes ya procesados
                        if self.stop_event.is_set(): break
                        msg_serialized = json.dumps(msg, sort_keys=True)
                        if msg_serialized not in current_history_messages_set:
                            self.conversation_history.append(msg)
                            current_history_messages_set.add(msg_serialized)
                    # --- FIN DE MODIFICACIÓN ---

                except InterruptedError:
                    print(f"[{self.bot_llm_choice}/{self.user_llm_choice}] Operación interrumpida por stop_event.")
                    break
                except Exception as e:
                    print(f"ERROR: Fallo crítico en el envío o generación de mensaje para {participant} en simulación {self.simulation_id}: {e}")
                    time.sleep(5) # Modificado
                
                if self.stop_event.is_set():
                    print(f"[{self.bot_llm_choice}/{self.user_llm_choice}] Simulación {self.simulation_id} abortada por señal de parada durante procesamiento de mensajes.")
                    break


        else: # Simulación sin interacción con la API (solo generación local pura)
            print(f"[User: {self.user_llm_choice}] Simulando conversación sin interacción con la API para {room_id}.")
            participants = [f"SimAgent_{i+1}_{self.user_llm_choice}" for i in range(self.num_participants)]

            for _ in range(self.num_messages_per_participant):
                if self.stop_event.is_set():
                    print(f"[{self.user_llm_choice}] Simulación {self.simulation_id} abortada por señal de parada.")
                    break

                for participant in participants:
                    if self.stop_event.is_set(): break
                    
                    formatted_history = []
                    for msg in self.conversation_history:
                        # Asegurarse de que los mensajes en el historial local para el prompt sean correctos.
                        # Aquí, solo necesitamos 'role' y 'content' para el LLM del usuario.
                        # El 'source' que se usa al final es para el CSV.
                        role = "user" if msg.get("user_name") != "Bot" else "assistant" # Ajuste para el historial de Langchain
                        formatted_history.append({"role": role, "content": msg.get("message", "")})

                    try:
                        if self.stop_event.is_set():
                            print(f"DEBUG: {self.user_llm_choice} - Detención solicitada antes de generate_message local.")
                            break
                        current_user_messages_sample = ' '.join(random.sample(sample_messages_list, min(len(sample_messages_list), 500))) if sample_messages_list else "No hay ejemplos de mensajes de usuario."
                        simulated_message = self.agent.generate_message(participant, formatted_history, self.case, current_user_messages_sample, self.conversation_type)

                        timestamp = datetime.now().isoformat()
                        # Aquí, para el caso sin bot, ya se incluyen metadata y timing_info vacíos
                        self.conversation_history.append({
                            "timestamp": timestamp,
                            "room_id": room_id,
                            "user_name": participant,
                            "message": simulated_message,
                            "source": "simulated_local",
                            "metadata": {}, # Aseguramos que está presente
                            "timing_info": {} # Aseguramos que está presente
                        })
                        print(f"[User: {self.user_llm_choice}] {participant}: {simulated_message}")
                        time.sleep(random.uniform(SIMULATION_INTERVAL * 0.5, SIMULATION_INTERVAL * 2)) # Modificado
                    except InterruptedError:
                        print(f"[{self.user_llm_choice}] Operación local interrumpida por stop_event.")
                        break
                    except Exception as e:
                        print(f"ERROR: Fallo crítico en la generación local de mensaje para {participant} en simulación {self.simulation_id}: {e}")
                        time.sleep(5) # Modificado
                
                if self.stop_event.is_set():
                    print(f"[{self.user_llm_choice}] Simulación {self.simulation_id} abortada por señal de parada durante generación local.")
                    break

        if not self.stop_event.is_set() or self.conversation_history:
            self._export_conversation_to_csv(room_id, use_bot=self.use_bot)
        else:
            print(f"[{self.bot_llm_choice}/{self.user_llm_choice}] Simulación {self.simulation_id} no exportada debido a interrupción temprana sin datos.")


    def _export_conversation_to_csv(self, room_id: str, use_bot: bool = True):
        """Exporta el historial de la conversación a un archivo CSV."""
        
        # Define un conjunto estándar de columnas que esperamos en el CSV
        standard_columns = [
            "timestamp", "room_id", "user_name", "message", "source",
            "metadata", "timing_info"
        ]

        uniform_history = []
        for msg in self.conversation_history:
            # Crear un nuevo diccionario para asegurar que todas las columnas estándar estén presentes
            uniform_msg = {col: msg.get(col) for col in standard_columns}
            
            # Asegurar que metadata y timing_info sean diccionarios (o listas), no None.
            # Convertirlos a cadenas JSON para el CSV.
            if uniform_msg.get("metadata") is None:
                uniform_msg["metadata"] = {}
            if uniform_msg.get("timing_info") is None:
                uniform_msg["timing_info"] = {}
            
            # Convertir diccionarios a cadenas JSON para compatibilidad con CSV
            try:
                uniform_msg["metadata"] = json.dumps(uniform_msg["metadata"])
            except TypeError:
                # Esto no debería ocurrir con la nueva lógica de parsing, pero se mantiene como un safeguard.
                uniform_msg["metadata"] = json.dumps({}) 
                print(f"      ADVERTENCIA: Fallback para metadata durante el volcado a CSV debido a TypeError para el mensaje: {uniform_msg.get('message', '')[:50]}")
            
            try:
                uniform_msg["timing_info"] = json.dumps(uniform_msg["timing_info"])
            except TypeError:
                # Esto no debería ocurrir con la nueva lógica de parsing, pero se mantiene como un safeguard.
                uniform_msg["timing_info"] = json.dumps({}) 
                print(f"      ADVERTENCIA: Fallback para timing_info durante el volcado a CSV debido a TypeError para el mensaje: {uniform_msg.get('message', '')[:50]}")

            uniform_history.append(uniform_msg)

        df = pd.DataFrame(uniform_history)

        if df.empty:
            print(f"[Bot: {self.bot_llm_choice}, User: {self.user_llm_choice}] No hay datos para exportar para la simulación {self.simulation_id}.")
            return

        bot_status = "con_bot" if use_bot else "sin_bot"
        filename = os.path.join(OUTPUT_DIR, f"conversation_{self.simulation_id}_room_{room_id}_Bot_{self.bot_llm_choice}_User_{self.user_llm_choice}_{bot_status}.csv")
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"[Bot: {self.bot_llm_choice}, User: {self.user_llm_choice}] Conversación {self.simulation_id} (Sala {room_id}, Bot: {bot_status}) exportada a: {filename}")


class MultiRoomSimulationManager:
    def __init__(self, room_manager: RoomManager, all_api_keys: Dict[str, str], user_messages_df: pd.DataFrame, cases_to_simulate: Dict, stop_event: Event):
        self.room_manager = room_manager
        self.all_api_keys = all_api_keys
        self.user_messages_df = user_messages_df
        self.cases_to_simulate = cases_to_simulate
        self.stop_event = stop_event

    def run_simulation_for_case(self, case_name: str, case_text: str, bot_llm_choice: str, user_llm_choice: str, conversation_type: str = "typical", simulation_id_prefix: str = None, use_bot: bool = True, stop_event: Event = None):
        """
        Ejecuta una única simulación para un caso y LLM dados.
        """
        if stop_event and stop_event.is_set():
            print(f"[{bot_llm_choice}/{user_llm_choice}] Simulación para '{case_name}' omitida debido a señal de parada.")
            return

        api_key_for_user_llm = self.all_api_keys.get(user_llm_choice)
        if not api_key_for_user_llm:
            print(f"[{user_llm_choice}] Advertencia: No se encontró API Key para el usuario {user_llm_choice}. Saltando simulación para '{case_name}'.")
            return

        if use_bot:
            api_key_for_bot_llm = self.all_api_keys.get(bot_llm_choice)
            if not api_key_for_bot_llm:
                print(f"[{bot_llm_choice}] Advertencia: No se encontró API Key para el bot {bot_llm_choice}. Saltando simulación para '{case_name}'.")
                return

        clean_bot_llm_choice = bot_llm_choice.lower().replace('-', '')
        clean_user_llm_choice = user_llm_choice.lower().replace('-', '')
        simulation_id = f"{simulation_id_prefix}_{clean_bot_llm_choice}_user_{clean_user_llm_choice}_{datetime.now().strftime('%H%M%S')}"

        simulation = Simulation(
            room_manager=self.room_manager,
            bot_llm_choice=bot_llm_choice,
            user_llm_choice=user_llm_choice,
            user_api_key=api_key_for_user_llm,
            num_participants=3,
            num_messages_per_participant=3,
            conversation_type=conversation_type,
            case=case_text,
            simulation_id=simulation_id,
            use_bot=use_bot,
            user_messages_df=self.user_messages_df,
            stop_event=stop_event
        )
        simulation.simulate()

    def run_all_simulations(self):
        """
        Ejecuta todas las simulaciones definidas en `cases_to_simulate` de forma secuencial.
        """
        timestamp_prefix = datetime.now().strftime("%Y%m%d")

        for case_name, simulations_configs in self.cases_to_simulate.items():
            for sim_config in simulations_configs:
                repetitions = sim_config.get("repetitions", 1)
                use_bot = sim_config.get("use_bot", True)
                bot_llm_choice = sim_config.get("bot_llm_choice")
                user_llm_choice = sim_config.get("user_llm_choice", bot_llm_choice)

                if not bot_llm_choice:
                    print(f"Advertencia: 'bot_llm_choice' no especificado para una configuración en '{case_name}'. Saltando.")
                    continue
                if not user_llm_choice:
                    print(f"Advertencia: 'user_llm_choice' no especificado para una configuración en '{case_name}'. Saltando.")
                    continue

                if bot_llm_choice not in self.all_api_keys or not self.all_api_keys.get(bot_llm_choice):
                    print(f"Advertencia: No se encontró API Key para el bot '{bot_llm_choice}' o el LLM no es válido. Saltando simulación de '{case_name}'.")
                    continue
                if user_llm_choice not in self.all_api_keys or not self.all_api_keys.get(user_llm_choice):
                    print(f"Advertencia: No se encontró API Key para el usuario '{user_llm_choice}' o el LLM no es válido. Saltando simulación de '{case_name}'.")
                    continue

                case_text = sim_config.get("case_text")
                if case_text is None:
                    if case_name == "caso_sebastian":
                        case_text = SEBASTIAN_CASE
                    else:
                        print(f"Advertencia: No se encontró el texto del caso para '{case_name}' en la configuración ni como SEBASTIAN_CASE. Saltando simulación.")
                        continue

                for i in range(repetitions):
                    if self.stop_event.is_set():
                        print(f"[{bot_llm_choice}/{user_llm_choice}] Abortando nuevas simulaciones debido a señal de parada.")
                        break

                    conversation_type = "typical"

                    bot_status_prefix = "conbot" if use_bot else "sinbot"
                    simulation_id_prefix = f"{timestamp_prefix}_{conversation_type}_{case_name}_bot_{bot_llm_choice.lower()}_user_{user_llm_choice.lower()}_{bot_status_prefix}"

                    print(f"\n--- Iniciando repetición {i+1}/{repetitions} para {case_name}, Bot: {bot_llm_choice}, User: {user_llm_choice}, Tipo: {bot_status_prefix} ---")
                    
                    # Llamada directa a la simulación, sin hilos
                    self.run_simulation_for_case(
                        case_name, case_text, bot_llm_choice, user_llm_choice, 
                        conversation_type, simulation_id_prefix, use_bot, self.stop_event
                    )
                    
                    if not self.stop_event.is_set():
                        # Pequeña pausa entre simulaciones completas para no saturar
                        time.sleep(random.uniform(5, 10)) 


        if not self.stop_event.is_set():
            print("\n--- Todas las simulaciones han finalizado con éxito ---")
        else:
            print("\n--- Las simulaciones fueron interrumpidas. Algunos resultados pueden estar incompletos ---")


# --- Función principal para ejecutar la simulación ---
def run_main_simulation():
    all_api_keys = {
        "ChatGPT": os.getenv("OPENAI_API_KEY"),
        "Gemini": os.getenv("GOOGLE_API_KEY"),
        "DeepSeek": os.getenv("DEEPSEEK_API_KEY"),
    }

    print("API Keys Cargadas (solo para referencia, los valores son sensibles):")
    for llm, key in all_api_keys.items():
        print(f"  {llm}: {'Configurada' if key else 'NO CONFIGURADA'}")

    # Verificación de la configuración de API_BASE_URL
    current_api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    # Este if/else es redundante si API_URL_PREFIX se define justo después
    # y ya maneja el prefijo https:// de forma robusta.
    # Pero si API_BASE_URL en el .env ya viene con https://, hay que ajustar
    # la construcción de API_URL_PREFIX.
    # La solución más robusta para API_URL_PREFIX es:
    global API_URL_PREFIX
    if current_api_base_url.startswith("https://"):
        # Si API_BASE_URL ya tiene https://, simplemente añadimos /api
        API_URL_PREFIX = f"{current_api_base_url}/api"
        print(f"ADVERTENCIA: API_BASE_URL '{current_api_base_url}' ya contiene 'https://'.")
        print(f"             Asegúrese de que el endpoint del servidor maneje la doble inclusión de prefijos si es relevante.")
    elif current_api_base_url.startswith("http://"):
        # Si API_BASE_URL tiene http://, lo convertimos a https://
        API_URL_PREFIX = f"https://{current_api_base_url[len('http://'):]}/api"
        print(f"ADVERTENCIA: API_BASE_URL '{current_api_base_url}' es 'http://'. Forzando 'https://'.")
    else:
        # Si es solo el host o host:port, agregamos https://
        API_URL_PREFIX = f"https://{current_api_base_url}/api"
        print(f"INFO: Usando API_BASE_URL '{current_api_base_url}' con prefijo 'https://'.")


    if not any(all_api_keys.values()) and "localhost" not in API_URL_PREFIX:
        print("Advertencia: No se encontraron API Keys configuradas en .env. Las simulaciones con bot podrían fallar si no es un entorno local.")

    room_manager = RoomManager(API_URL_PREFIX)

    cases_to_simulate = {
        "caso_sebastian": [
            {"repetitions": 1, "use_bot": True, "bot_llm_choice": "ChatGPT", "user_llm_choice": "ChatGPT", "case_text": SEBASTIAN_CASE},
            {"repetitions": 1, "use_bot": True, "bot_llm_choice": "Gemini", "user_llm_choice": "Gemini", "case_text": SEBASTIAN_CASE},
            {"repetitions": 1, "use_bot": True, "bot_llm_choice": "DeepSeek", "user_llm_choice": "DeepSeek", "case_text": SEBASTIAN_CASE},

            {"repetitions": 1, "use_bot": True, "bot_llm_choice": "ChatGPT", "user_llm_choice": "Gemini", "case_text": SEBASTIAN_CASE},
            {"repetitions": 1, "use_bot": True, "bot_llm_choice": "Gemini", "user_llm_choice": "ChatGPT", "case_text": SEBASTIAN_CASE},
            {"repetitions": 1, "use_bot": True, "bot_llm_choice": "DeepSeek", "user_llm_choice": "ChatGPT", "case_text": SEBASTIAN_CASE},
            {"repetitions": 1, "use_bot": True, "bot_llm_choice": "ChatGPT", "user_llm_choice": "DeepSeek", "case_text": SEBASTIAN_CASE},

            {"repetitions": 1, "use_bot": False, "bot_llm_choice": "ChatGPT", "user_llm_choice": "ChatGPT", "case_text": SEBASTIAN_CASE},
            {"repetitions": 1, "use_bot": False, "bot_llm_choice": "Gemini", "user_llm_choice": "Gemini", "case_text": SEBASTIAN_CASE},
            {"repetitions": 1, "use_bot": False, "bot_llm_choice": "DeepSeek", "user_llm_choice": "DeepSeek", "case_text": SEBASTIAN_CASE},
            {"repetitions": 1, "use_bot": False, "bot_llm_choice": "ChatGPT", "user_llm_choice": "DeepSeek", "case_text": SEBASTIAN_CASE},
        ],
    }

    global global_stop_event
    global_stop_event = Event()

    multi_room_manager = MultiRoomSimulationManager(room_manager, all_api_keys, user_messages_df, cases_to_simulate, global_stop_event)
    print("\n--- Ejecutando las simulaciones (modo secuencial) ---")
    try:
        multi_room_manager.run_all_simulations()
    except KeyboardInterrupt:
        print("\nSe detectó CTRL+C. Señalando para terminar de forma limpia...")
        global_stop_event.set() # Esto le dice a las funciones que revisen y salgan de sus bucles
        # Ya no hay hilos que esperar, la salida será más directa
        print("La operación actual intentará finalizar de forma controlada.")
    finally:
        print("\n--- Simulación de conversaciones finalizada o interrumpida. Los archivos CSV se han guardado en la carpeta 'simulated_conversations' ---")
        sys.exit(0)

if __name__ == "__main__":
    run_main_simulation()