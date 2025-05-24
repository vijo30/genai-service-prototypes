# chat_test.py
import requests
import time
import random
from datetime import datetime
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from config.generated_config import SEBASTIAN_CASE
from langchain_core.output_parsers import StrOutputParser
import pandas as pd
from langchain_core.runnables  import Runnable

load_dotenv()

API_BASE_URL = "https://" + os.getenv("API_BASE_URL") + '/api'
SIMULATION_INTERVAL = 5 * 2 # Aumentamos el intervalo base
LLM_NAME = os.getenv("LLM_NAME", "ChatGPT")
OPENAI_API_KEY = os.getenv("API_KEY")
USER_MESSAGES_CSV = ".data_usr_msg.csv"
OUTPUT_DIR = "simulated_conversations"

os.makedirs(OUTPUT_DIR, exist_ok=True)


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
        """Inicializa el modelo de lenguaje adecuado."""
        if self.llm_name == 'ChatGPT':
            return ChatOpenAI(model="gpt-3.5-turbo", temperature=0.5, api_key=self.api_key)
        elif self.llm_name == 'Gemini':
            return ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.5, google_api_key=self.api_key)
        else:
            raise ValueError(f"Modelo de lenguaje no soportado: {self.llm_name}")

    def build_typical_user_chain(self) -> Runnable:
      """Construye la cadena para generar mensajes como un usuario típico de EthicApp,
      caracterizado por un nivel de discusión no muy profundo, similar a los ejemplos.
      """
      prompt = ChatPromptTemplate.from_messages([
          HumanMessagePromptTemplate.from_template(
              """Eres {participant_name}, un estudiante universitario típico participando en un debate ético sobre el caso de Sebastián.

              Tu objetivo es generar un mensaje corto (entre 3 y 6 oraciones) que refleje la forma en que los estudiantes suelen expresarse en EthicApp, caracterizada por un nivel de discusión que NO suele ser muy profundo ni con argumentos elaborados.
              Los mensajes tienden a ser más directos, expresando opiniones iniciales, reacciones al caso o comentarios breves sobre lo que otros han dicho, sin necesariamente profundizar en el razonamiento o presentar contraargumentos detallados.

              Es fundamental que tu forma de expresarte, incluyendo el uso de mayúsculas, minúsculas, errores ortográficos leves, la extensión de los mensajes
              y el contenido general, sea LO MÁS SIMILAR POSIBLE a los siguientes ejemplos de mensajes reales de usuarios de EthicApp:
              {user_messages}

              Considera el siguiente caso:
              {case}

              Este es el historial de conversación reciente:
              {conversation_history}

              Genera un mensaje que sea típico de la participación de los estudiantes en EthicApp, manteniendo un nivel de discusión similar al que se observa en los ejemplos.
              """
          )
      ])
      return prompt | self.llm | self.output_parser

    def generate_message(self, participant_name, conversation_history, case, user_messages, conversation_type="typical"):
        """Genera un mensaje como un usuario típico."""
        if conversation_type not in self.chains:
            raise ValueError(f"Tipo de conversación no soportado: {conversation_type}")

        chain = self.chains[conversation_type]
        return chain.invoke({
            "participant_name": participant_name,
            "conversation_history": conversation_history,
            "case": case,
            "user_messages": user_messages,
        })



class RoomManager:
    """Clase para gestionar las salas de chat."""

    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url

    def create_room(self):
        """Crea una nueva sala de chat."""
        try:
            response = requests.post(f"{self.api_base_url}/create_room")
            response.raise_for_status()
            return response.json().get("room_id")
        except requests.exceptions.RequestException as e:
            print(f"Error al crear la sala: {e}")
            return None

    def set_username(self, room_id: str, username: str):
        """Establece un nombre de usuario para la sesión."""
        try:
            session = requests.Session()
            response = session.post(f"{self.api_base_url}/set_username", json={"username": username})
            response.raise_for_status()
            return session.cookies
        except requests.exceptions.RequestException as e:
            print(f"Error al establecer el nombre de usuario: {e}")
            return None

    def send_message(self, room_id: str, username: str, message: str, cookies=None, retry_delay=5, max_retries=3):
        """Envía un mensaje simulado con manejo de reintentos para rate limits."""
        headers = {"Content-Type": "application/json"}
        url = f"{self.api_base_url}/simulate_message"
        data = {"room_id": room_id, "user_name": username, "message": message}
        for attempt in range(max_retries):
            try:
                if cookies:
                    response = requests.post(url, headers=headers, json=data, cookies=cookies)
                else:
                    response = requests.post(url, headers=headers, json=data)
                response.raise_for_status()
                return True
            except requests.exceptions.RequestException as e:
                print(f"Error al enviar el mensaje de {username} (Intento {attempt + 1}/{max_retries}): {e}")
                if response is not None and response.status_code == 429:
                    print(f"Se alcanzó el límite de frecuencia. Reintentando en {retry_delay} segundos...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Retraso exponencial
                else:
                    return False  # Otro error, no reintentar
        print(f"Falló el envío del mensaje de {username} después de {max_retries} intentos.")
        return False
      
    def get_recent_messages(self, room_id: str, limit: int = 50):
        """Obtiene los mensajes recientes de la sala."""
        try:
            response = requests.get(f"{API_BASE_URL}/chat/{room_id}")
            response.raise_for_status()
            messages = response.json().get("messages", [])
            return messages[-limit:]
        except requests.exceptions.RequestException as e:
            print(f"Error al obtener mensajes recientes: {e}")
            return []


class Simulation:
    """Clase para gestionar la simulación de conversaciones y exportarlas a CSV."""

    def __init__(self, room_manager: RoomManager, agent: LLMAgent, num_participants: int, case: str = SEBASTIAN_CASE, num_messages_per_participant: int = 5, conversation_type="typical", simulation_id=None, use_bot=True):
        self.room_manager = room_manager
        self.agent = agent
        self.num_participants = num_participants
        self.num_messages_per_participant = num_messages_per_participant
        self.conversation_type = conversation_type
        self.case = case
        self.conversation_history = []
        self.simulation_id = simulation_id if simulation_id else datetime.now().strftime("%Y%m%d_%H%M%S")
        self.use_bot = use_bot

    def simulate(self):
        """Simula una conversación y guarda el historial en un CSV."""
        room_id = "no_api_" + self.simulation_id if not self.use_bot else self.room_manager.create_room()
        if not room_id and self.use_bot:
            return

        simulation_type_str = "con_bot" if self.use_bot else "sin_bot"
        print(f"Simulación ID: {self.simulation_id}, Bot: {simulation_type_str}")
        participants = [f"SimAgent_{i+1}" for i in range(self.num_participants)]
        participant_sessions = {}
        has_participated = [False] * self.num_participants
        messages_sent_by_user = [0] * self.num_participants

        if self.use_bot:
            for i, participant in enumerate(participants):
                cookies = self.room_manager.set_username(room_id, participant)
                if cookies:
                    participant_sessions[participant] = cookies
                    print(f"{participant} se unió a la sala.")
                    time.sleep(0.5)
                else:
                    has_participated[i] = True

            total_user_messages = self.num_messages_per_participant * self.num_participants
            user_messages_count = 0

            while user_messages_count < total_user_messages:
                available_participants = [i for i, participated in enumerate(has_participated) if not participated]

                if available_participants:
                    participant_index = random.choice(available_participants)
                    participant = participants[participant_index]
                    recent_messages = self.room_manager.get_recent_messages(room_id)
                    sample_size = min(5000, len(user_messages_df))
                    sample = ' '.join(random.sample(user_messages_df['message'].tolist(), sample_size))
                    simulated_message = self.agent.generate_message(participant, recent_messages, self.case, sample, self.conversation_type)
                    cookies = participant_sessions.get(participant)

                    if self.room_manager.send_message(room_id, participant, simulated_message, cookies):
                        print(f"{participant}: {simulated_message}")
                        user_messages_count += 1
                        messages_sent_by_user[participant_index] += 1
                        if messages_sent_by_user[participant_index] >= self.num_messages_per_participant:
                            has_participated[participant_index] = True
                        time.sleep(random.uniform(SIMULATION_INTERVAL * 0.5, SIMULATION_INTERVAL * 2))
                        time.sleep(1)
                    else:
                        pass
                else:
                    break

                all_messages = self.room_manager.get_recent_messages(room_id, limit=1000)
                for msg in all_messages:
                    if msg not in [hist_msg for hist_msg in self.conversation_history if hist_msg['timestamp'] == msg['timestamp']]:
                        self.conversation_history.append(msg)
        else:
            # Simulación sin interacción con la API
            print("Simulando conversación sin interacción con la API.")
            participants = [f"SimAgent_{i+1}" for i in range(self.num_participants)]
            for i in range(self.num_messages_per_participant):
                for participant in participants:
                    recent_history = [msg['message'] for msg in self.conversation_history if msg['user_name'] == participant][-50:] # Considerar los últimos mensajes del participante
                    sample_size = min(5000, len(user_messages_df))
                    sample = ' '.join(random.sample(user_messages_df['message'].tolist(), sample_size))
                    simulated_message = self.agent.generate_message(participant, recent_history, self.case, sample, self.conversation_type)
                    timestamp = datetime.now().isoformat()
                    self.conversation_history.append({"timestamp": timestamp, "room_id": room_id, "user_name": participant, "message": simulated_message})
                    print(f"{participant}: {simulated_message}")
                    time.sleep(random.uniform(SIMULATION_INTERVAL * 0.5, SIMULATION_INTERVAL * 2))

        self._export_conversation_to_csv(room_id, use_bot=self.use_bot)

    def _export_conversation_to_csv(self, room_id, use_bot=True):
        """Exporta el historial de la conversación a un archivo CSV."""
        df = pd.DataFrame(self.conversation_history)
        bot_status = "con_bot" if use_bot else "sin_bot"
        filename = os.path.join(OUTPUT_DIR, f"conversation_{self.simulation_id}_{room_id}_{bot_status}.csv")
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"Conversación {self.simulation_id} (Sala {room_id}, Bot: {bot_status}) exportada a: {filename}")



def load_user_messages(csv_path: str) -> pd.DataFrame:
    """Carga los mensajes de usuario desde un archivo CSV."""
    try:
        df = pd.read_csv(csv_path)
        if 'user_id' not in df.columns or 'message' not in df.columns:
            raise ValueError("El archivo CSV debe contener las columnas 'user_id' y 'message'.")
        return df
    except FileNotFoundError:
        print(f"Error: El archivo CSV '{csv_path}' no fue encontrado.")
        return pd.DataFrame()
    except pd.errors.EmptyDataError:
        print(f"Error: El archivo CSV '{csv_path}' está vacío.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error inesperado al leer el archivo CSV '{csv_path}': {e}")
        return pd.DataFrame()


base_dir = os.path.dirname(os.path.abspath(__file__))
historical_messages_csv = os.path.join(base_dir, ".data_usr_msg.csv")
user_messages_df = load_user_messages(historical_messages_csv)

if user_messages_df.empty:
    print("No se pudieron cargar los mensajes del usuario. La simulación podría no funcionar como se espera.")
    
    

from threading import Thread

class MultiRoomSimulationManager:
    def __init__(self, room_manager, agent, user_messages_df, cases_to_simulate: dict):
        """
        Inicializa el MultiRoomSimulationManager.
        """
        self.room_manager = room_manager
        self.agent = agent
        self.user_messages_df = user_messages_df
        self.cases_to_simulate = cases_to_simulate

    def run_simulation_for_case(self, case_name, case_text, conversation_type="typical", simulation_id_prefix=None, use_bot=True):
        simulation_id = f"{simulation_id_prefix}_{case_name}_{datetime.now().strftime('%H%M%S')}" if simulation_id_prefix else f"{case_name}_{datetime.now().strftime('%H%M%S')}"
        simulation = Simulation(
            room_manager=self.room_manager,
            agent=self.agent,
            num_participants=3,  # Ajusta según necesites
            num_messages_per_participant=3,  # Ajusta según necesites
            conversation_type=conversation_type,
            case=case_text,
            simulation_id=simulation_id,
            use_bot=use_bot
        )
        simulation.simulate()

    def run_all_simulations(self):
        threads = []
        timestamp_prefix = datetime.now().strftime("%Y%m%d")
        for case_name, simulations in self.cases_to_simulate.items():
            case_text = self.cases_to_simulate[case_name][0].get("case_text")
            if case_text is None and case_name == "caso_sebastian":
                case_text = SEBASTIAN_CASE
            elif case_text is None:
                print(f"Advertencia: No se encontró el texto del caso para '{case_name}'.")
                continue

            for sim_config in simulations:
                repetitions = sim_config.get("repetitions", 1)
                use_bot = sim_config.get("use_bot", True)
                for i in range(repetitions):
                    for conversation_type in self.agent.chains.keys():
                        bot_status_prefix = "conbot" if use_bot else "sinbot"
                        simulation_id_prefix = f"{timestamp_prefix}_{conversation_type}_{case_name}_{bot_status_prefix}_noapi" if not use_bot else f"{timestamp_prefix}_{conversation_type}_{case_name}_{bot_status_prefix}_api"
                        t = Thread(target=self.run_simulation_for_case, args=(case_name, case_text, conversation_type, simulation_id_prefix, use_bot))
                        t.start()
                        threads.append(t)
                        time.sleep(2)

        for t in threads:
            t.join()


if __name__ == "__main__":
    # --- Inicializa los objetos ---
    agent = LLMAgent(LLM_NAME, OPENAI_API_KEY)
    room_manager = RoomManager(API_BASE_URL)
    

    # --- Define los casos a simular con el número de repeticiones y configuración del bot ---
    cases_to_simulate = {
        "caso_sebastian": [
            {"repetitions": 1, "use_bot": True, "case_text": SEBASTIAN_CASE},  # Caso con bot (interacción API)
            {"repetitions": 1, "use_bot": False, "case_text": SEBASTIAN_CASE}, # Caso sin bot (generación local)
        ],
        # "otro_caso": [
        #     {"repetitions": 1, "use_bot": True, "case_text": "Texto del otro caso..."},
        #     {"repetitions": 1, "use_bot": False, "case_text": "Texto del otro caso..."}
        # ],
    }

    # --- Ejecuta las simulaciones ---
    multi_room_manager = MultiRoomSimulationManager(room_manager, agent, user_messages_df, cases_to_simulate)
    print("\n--- Ejecutando las simulaciones ---")
    multi_room_manager.run_all_simulations()
    print("\n--- Simulación de conversaciones finalizada. Los archivos CSV se han guardado en la carpeta 'simulated_conversations' ---")

    