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
from config.generated_config import SEBASTIAN_CASE
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

API_BASE_URL = "https://" + os.getenv("API_BASE_URL") + '/api'  # Ajusta la URL de tu backend
SIMULATION_INTERVAL = 2  # Tiempo en segundos entre mensajes simulados
LLM_NAME = os.getenv("LLM_NAME", "ChatGPT") # Default a ChatGPT si no está en .env
OPENAI_API_KEY = os.getenv("API_KEY") # Asegúrate de tener tu API key en .env

def initialize_llm():
    """Inicializa el modelo de lenguaje."""
    if LLM_NAME == 'ChatGPT':
        return ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7, api_key=OPENAI_API_KEY)
    elif LLM_NAME == 'Gemini':
        return ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.7, google_api_key=OPENAI_API_KEY)
    else:
        raise ValueError(f"Modelo de lenguaje no soportado: {LLM_NAME}")

llm = initialize_llm()

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

def generate_simulated_message(participant_name, conversation_history, case, conversation_type="ideal"):
    """Genera un mensaje simulado usando un LLM."""
    if conversation_type == "ideal":
        prompt_template = f"""Eres {{participant_name}}, un participante en un debate ético sobre el caso de Sebastián.
        Genera un mensaje corto (máximo 100 palabras) que contribuya a una discusión reflexiva y ética sobre el dilema que enfrenta Sebastián.
        Intenta explorar diferentes perspectivas, posibles soluciones éticas y las implicaciones de las decisiones.

        Caso:
        {{case}}

        Historial de conversación reciente:
        {{conversation_history}}
        """
    elif conversation_type == "problematic":
        prompt_template = f"""Eres {{participant_name}}, un participante en un debate ético sobre el caso de Sebastián.
        Tu rol en esta conversación es explorar activamente formas en las que Sebastián podría hacer trampa sin ser descubierto, o minimizar las consecuencias negativas de hacerlo. No te preocupas demasiado por la integridad académica en este momento, tu principal interés es ayudar a Sebastián a salir de su apuro de la manera más fácil posible. También puedes ser un poco cortante o ignorar las preocupaciones éticas planteadas por otros.

        Caso:
        {{case}}

        Historial de conversación reciente:
        {{conversation_history}}

        Genera un mensaje corto (máximo 100 palabras) que sugiera una estrategia para hacer trampa, minimice la gravedad de la acción, cuestione la importancia de la honestidad, o sea un poco despectivo con las preocupaciones éticas.
        """
    else:
        raise ValueError(f"Tipo de conversación no soportado: {conversation_type}")

    prompt = PromptTemplate.from_template(prompt_template)
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({
        "participant_name": participant_name,
        "conversation_history": conversation_history,
        "case": case,
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
    """Simula una conversación con múltiples participantes cuyos mensajes son generados por agentes."""
    room_id = create_room()
    if not room_id:
        return

    print(f"Sala de chat creada con ID: {room_id} (Tipo: {conversation_type})")
    participants = [f"SimAgent_{i+1}" for i in range(num_participants)]
    participant_sessions = {}

    # Establecer nombres de usuario para cada participante
    for participant in participants:
        cookies = set_username(room_id, participant)
        if cookies:
            participant_sessions[participant] = cookies
            print(f"{participant} se unió a la sala.")
            time.sleep(0.5)

    conversation_history = []

    # Simular el envío de mensajes por los agentes
    for i in range(num_messages_per_participant * num_participants):
        participant = random.choice(participants)
        recent_messages = get_recent_messages(room_id)
        simulated_message = generate_simulated_message(participant, recent_messages, SEBASTIAN_CASE, conversation_type)
        cookies = participant_sessions.get(participant)
        if send_message(room_id, participant, simulated_message, cookies):
            print(f"{participant}: {simulated_message}")
            conversation_history.append({"user_name": participant, "message": simulated_message})
            time.sleep(random.uniform(SIMULATION_INTERVAL * 0.8, SIMULATION_INTERVAL * 1.2)) # Intervalo aleatorio
            time.sleep(1) # Pequeña pausa para el backend

if __name__ == "__main__":
    # --- Elige la simulación que quieres ejecutar ---

    # Caso de conversación ideal (sin intervención del agente ético)
    # print("\n--- Simulación de Conversación Ideal ---")
    # simulate_conversation_with_agents(num_participants=3, num_messages_per_participant=5, conversation_type="ideal")

    # Caso de conversación problemática (debería activar al agente ético)
    print("\n--- Simulación de Conversación Problemática ---")
    simulate_conversation_with_agents(num_participants=2, num_messages_per_participant=5, conversation_type="problematic")

    print("Simulación de conversación finalizada.")