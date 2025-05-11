import requests
import json
import time
import random
from datetime import datetime
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from config.generated_config import SEBASTIAN_CASE
from langchain_core.output_parsers import StrOutputParser
import pandas as pd

load_dotenv()

API_BASE_URL = "https://" + os.getenv("API_BASE_URL") + '/api'  # Ajusta la URL de tu backend
SIMULATION_INTERVAL = 2  # Tiempo en segundos entre mensajes simulados
LLM_NAME = os.getenv("LLM_NAME", "ChatGPT") # Default a ChatGPT si no está en .env
OPENAI_API_KEY = os.getenv("API_KEY") # Asegúrate de tener tu API key en .env
USER_MESSAGES_CSV = ".data_usr_msg.csv" # Ruta al archivo CSV con mensajes reales

def initialize_llm():
    """Inicializa el modelo de lenguaje."""
    if LLM_NAME == 'ChatGPT':
        return ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7, api_key=OPENAI_API_KEY)
    elif LLM_NAME == 'Gemini':
        return ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.7, google_api_key=OPENAI_API_KEY)
    else:
        raise ValueError(f"Modelo de lenguaje no soportado: {LLM_NAME}")

llm = initialize_llm()

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

def create_room():
    """Crea una nueva sala de chat."""
    try:
        response = requests.post(f"{API_BASE_URL}/create_room")
        response.raise_for_status()
        return response.json().get("room_id")
    except requests.exceptions.RequestException as e:
        print(f"Error al crear la sala: {e}")
        return None

def set_username(room_id: str, username: str):
    """Establece un nombre de usuario para la sesión."""
    try:
        session = requests.Session()
        response = session.post(f"{API_BASE_URL}/set_username", json={"username": username})
        response.raise_for_status()
        return session.cookies
    except requests.exceptions.RequestException as e:
        print(f"Error al establecer el nombre de usuario: {e}")
        return None

def send_message(room_id: str, username: str, message: str, cookies=None):
    """Envía un mensaje simulado a través de la ruta de simulación."""
    try:
        data = {"room_id": room_id, "user_name": username, "message": message}
        headers = {"Content-Type": "application/json"}
        url = f"{API_BASE_URL}/simulate_message"  # Nueva ruta para simulación
        if cookies:
            response = requests.post(url, headers=headers, json=data, cookies=cookies)
        else:
            response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error al enviar el mensaje de {username}: {e}")
        return False

def get_timestamp():
    """Genera un timestamp estandarizado."""
    return datetime.utcnow().isoformat() + "Z"

def generate_simulated_message(participant_name, conversation_history, case, user_messages , conversation_type="ideal"):
    """Genera un mensaje simulado usando un LLM condicionado por el estilo de los mensajes reales."""

        

    if conversation_type == "ideal":
        prompt = ChatPromptTemplate.from_messages([
            HumanMessagePromptTemplate.from_template(f"""Eres {{participant_name}}, un participante en un debate ético sobre el caso de Sebastián.
            Tu objetivo es generar un mensaje corto (máximo 3 oraciones) que contribuya a una discusión reflexiva y ética sobre el dilema que enfrenta Sebastián.
            Intenta expresarte de una manera FIELMENTE similar a los siguientes mensajes de chat reales, incluyendo minúsculas y palabras no tan bien escritas, también la extensión:
            {{user_messages}}

            Considera el siguiente caso:
            {{case}}

            Este es el historial de conversación reciente:
            {{conversation_history}}
            """)
        ])
    elif conversation_type == "problematic":
        prompt = ChatPromptTemplate.from_messages([
            HumanMessagePromptTemplate.from_template(f"""Eres {{participant_name}}, un participante en un debate ético sobre el caso de Sebastián.
            Tu rol en esta conversación es explorar activamente formas en las que Sebastián podría hacer trampa sin ser descubierto (máximo 3 oraciones), o minimizar las consecuencias negativas de hacerlo. No te preocupas demasiado por la integridad académica en este momento, tu principal interés es ayudar a Sebastián a salir de su apuro de la manera más fácil posible. También puedes ser un poco cortante o ignorar las preocupaciones éticas planteadas por otros.
            Intenta expresarte de una manera FIELMENTE similar a los siguientes mensajes de chat reales, incluyendo minúsculas y palabras no tan bien escritas, también la extensión:
            {{user_messages}}

            Considera el siguiente caso:
            {{case}}

            Este es el historial de conversación reciente:
            {{conversation_history}}
            """)
        ])
    else:
        raise ValueError(f"Tipo de conversación no soportado: {conversation_type}")

    chain = prompt | llm | StrOutputParser()
    return chain.invoke({
        "participant_name": participant_name,
        "conversation_history": conversation_history,
        "case": case,
        "user_messages": user_messages,
    })

def get_recent_messages(room_id: str, limit: int = 5):
    """Obtiene los mensajes recientes de la sala."""
    try:
        response = requests.get(f"{API_BASE_URL}/chat/{room_id}")
        response.raise_for_status()
        messages = response.json().get("messages", [])
        return messages[-limit:]
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener mensajes recientes: {e}")
        return []

def simulate_conversation_with_agents(num_participants: int, num_messages_per_participant: int = 5, conversation_type="ideal"):
    """Simula una conversación con múltiples participantes asegurando que todos participen al menos una vez."""
    room_id = create_room()
    if not room_id:
        return

    print(f"Sala de chat creada con ID: {room_id} (Tipo: {conversation_type})")
    participants = [f"SimAgent_{i+1}" for i in range(num_participants)]
    participant_sessions = {}
    has_participated = [False] * num_participants  # Registro de quién ha participado

    # Establecer nombres de usuario para cada participante
    for i, participant in enumerate(participants):
        cookies = set_username(room_id, participant)
        if cookies:
            participant_sessions[participant] = cookies
            print(f"{participant} se unió a la sala.")
            time.sleep(0.5)
        else:
            has_participated[i] = True # Considerar como "participado" si no se pudo unir

    conversation_history = []
    messages_sent = 0
    total_messages = num_messages_per_participant * num_participants

    while messages_sent < total_messages:
        # Priorizar a los participantes que aún no han enviado un mensaje
        available_participants = [i for i, participated in enumerate(has_participated) if not participated]

        if available_participants:
            participant_index = random.choice(available_participants)
        else:
            # Si todos han participado al menos una vez, seleccionar aleatoriamente
            participant_index = random.randrange(num_participants)

        participant = participants[participant_index]
        recent_messages = get_recent_messages(room_id)
        sample_size = min(5000, len(user_messages_df))
        sample = ' '.join(random.sample(user_messages_df['message'].tolist(), sample_size))
        simulated_message = generate_simulated_message(participant, recent_messages, SEBASTIAN_CASE, sample, conversation_type)
        cookies = participant_sessions.get(participant)

        if send_message(room_id, participant, simulated_message, cookies):
            print(f"{participant}: {simulated_message}")
            conversation_history.append({"user_name": participant, "message": simulated_message})
            has_participated[participant_index] = True
            messages_sent += 1
            time.sleep(random.uniform(SIMULATION_INTERVAL * 0.8, SIMULATION_INTERVAL * 1.2)) # Intervalo aleatorio
            time.sleep(1) # Pequeña pausa para el backend
        else:
            # Si falla el envío del mensaje, intentaremos con otro participante en la siguiente iteración
            pass

        # Si todos han participado y todavía faltan mensajes, reiniciar el registro
        if all(has_participated) and messages_sent < total_messages:
            has_participated = [False] * num_participants

if __name__ == "__main__":
    # --- Elige la simulación que quieres ejecutar ---

    # Caso de conversación ideal (sin intervención del agente ético)
    print("\n--- Simulación de Conversación Ideal ---")
    simulate_conversation_with_agents(num_participants=3, num_messages_per_participant=1, conversation_type="ideal")

    # Caso de conversación problemática (debería activar al agente ético)
    #print("\n--- Simulación de Conversación Problemática con Estilo del CSV (Participación Asegurada) ---")
    #simulate_conversation_with_agents(num_participants=3, num_messages_per_participant=1, conversation_type="problematic")

    print("Simulación de conversación finalizada.")