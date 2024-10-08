import logging
import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("API_KEY")

llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=OPENAI_API_KEY)

prompt = "Responde con True si el texto es parte de una discución ética. Responde con False en caso contrario."


def get_response(user_input, context, prompt=prompt):
  try:
     # Crear el prompt con historial de la sala
    full_prompt = f"{prompt}\n\n{context}\nUsuario: {user_input}\nAsistente:"
    response = llm.predict(full_prompt) 
    return response
  except Exception as error:
    logging.exception("message")
    return str(error)