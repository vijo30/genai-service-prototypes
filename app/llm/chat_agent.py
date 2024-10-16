import logging
import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("API_KEY")

llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=OPENAI_API_KEY)

prompt = "Responde con True si el texto es parte de una discución ética. Responde con False en caso contrario."

def should_react_to_conversation(messages):
    context = "\n".join([f"{msg['user_name']}: {msg['message']}" for msg in messages[-10:]])
    full_prompt = f"""La siguiente es una conversación en un debate sobre ética profesional. Evalúa si la conversación sigue enfocada en el tema ético o si los participantes se han desviado del objetivo.
    Incluye mensajes de bot y de usuario. Fijate si los usuarios denominados user con su numero respectivo se desvian de la conversacion.
    
Conversación reciente:
{context}

Responde con "True" si la conversación ha perdido el foco y los participantes están hablando de otro tema. Responde con "False" si la conversación sigue enfocada en el tema ético."""

    print(full_prompt)
    
    response = llm.predict(full_prompt)
    
    return response == 'True'

def get_response(message, context):
  try:
    full_prompt = f"""La siguiente es una conversación en un debate sobre ética profesional. Tu objetivo es responder de manera que mantengas la conversación centrada en el tema ético. Considera el siguiente contexto antes de responder:
    
Contexto de la conversación reciente:
{context}

Usuario: {message}

Responde como un asistente que fomenta la discusión ética y evita distracciones."""
    response = llm.predict(full_prompt)
    return response
  except Exception as error:
    logging.exception("message")
    return str(error)