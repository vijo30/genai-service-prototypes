import json
import logging
import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("API_KEY")

llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=OPENAI_API_KEY)


caso_etico = """
Debes seguir la guia del Caso Sebastian, que es el siguiente:

CASO “SEBASTIÁN”

Creo que me fue bien en la prueba de matemáticas. Eso sí, en la parte de álgebra lineal tan bien no me fue, pero creo que salvé con las otras preguntas. 
Justo estaba por salir a tomarme unas cervezas a la casa de una amiga, cuando me llamó Sebastián, mi mejor amigo, para decirme que estaba complicado con el examen de contabilidad; que había estudiado harto pero que creía que no iba a lograr la nota para aprobar el curso. Lo entiendo, el curso es bastante difícil. Es cierto que yo me eximí, pero de que lo pasé mal durante el semestre con los ejercicios y las solemnes, lo pasé mal. 
Durante la conversación, Sebastián se notaba muy nervioso y angustiado; tan angustiado que yo mismo comencé a angustiarme. No es para menos, si reprueba el curso se atrasa un año y no tendrá dinero para pagar el cuota de la carrera (Sebastián estudia con gratuidad completa). Muchas veces hemos discutido esto con los papás de Sebastián cuando estamos almorzando o cenando en su casa. Ellos son una familia esforzada: ambos papás trabajan para poder sacar adelante a la Francisca y a Sebastián. No entienden por qué han puesto esta regla de financiar sólo los 5 años que dura la carrera (de acuerdo al plan de estudios), cuando todos sabemos que la mayoría de los estudiantes no logra terminarla en ese tiempo. 
A pesar de todo el esfuerzo que realizan, los papás de Sebastián, Alberto y Alejandra, son muy generosos y acogedores. Me recibieron durante un par de meses en plena pandemia, cuando tenía problemas con mi propia familia, sin poner complicaciones cuando Sebastián preguntó si acaso podía quedarme con ellos un tiempo. En ese tiempo me di cuenta de que Alberto, Alejandra, Sebastián y Francisca son una familia trabajadora y honrada, que no quiere nada regalado.   
Durante mi estadía con la familia de Sebastián, estudiamos juntos en múltiples ocasiones. Con el tiempo, él me ayudó en los ramos que más me costaban, y viceversa. Pero había un ramo con el cual Sebastián batallaba incesantemente: contabilidad. Volví a mi casa, arreglé las cosas con mi familia y, en unos meses, la pandemia comenzó a menguar: había menos restricciones para moverse y era más fácil salir de la casa, pero, por seguridad, los ramos los seguíamos teniendo online. Por eso no me extrañó que, visiblemente incómodo, Sebastián me pidiera que lo ayudara a contestar el examen de contabilidad. Me imagino la angustia y vergüenza que debe haber tenido para pedírmelo. Ahí entendí por qué me había llamado por teléfono y no había venido a la casa para hablar un tema tan importante.
Le pregunté a Sebastián por qué tenía tanta vergüenza. Me dijo que, al hablar con su papá, éste le dijo que no podía darse el lujo de reprobar un ramo, que tenía que pasarlo sí o sí, estudiando día y noche, o de otro modo la familia se vería en serios problemas financieros. Pero le dejó muy claro, también que: “en esta familia nos ganamos las cosas, nadie nos regaló nada y no hacemos las cosas a medias o tomando atajos; trabaja duro y verás los resultados”. Y Alejandra, su mamá, le sugirió que hablara conmigo, para que lo ayudara. Después de todo, Sebastián me había ayudado “en las malas”, ¿por qué no iba a hacer lo mismo por él? Sebastián me dijo que estaba muy confundido, sabe que lo que pide me compromete, pero no ve mucha salida al problema. 
Ni a Sebastián ni a mí nos gusta esto de la copia. De hecho, muchas veces hemos peleado con algunos compañeros porque nos hemos sentido perjudicados por su comportamiento: “ustedes sacan mejor nota que nosotros que no copiamos”, es lo que siempre les decimos. Incluso lo hemos hablado con varios profesores, porque nos molesta mucho que las conductas deshonestas finalmente sean premiadas. Parece que nos gusta vivir en un país en el que “hacerse el vivo” es una cualidad positiva. Los docentes siempre nos han dicho que, al final, por mucho que nuestros compañeros saquen mejores notas, serán siempre peores profesionales que nosotros: primero porque saldremos de la carrera literalmente sabiendo más (y, por consiguiente, mejor preparados); en segundo lugar, porque la honestidad y el trabajo esforzado son virtudes tremendamente deseables en el ámbito laboral. De todas formas, siempre quedamos con la sensación desagradable de que los compañeros que hacen trampa nos pasan a llevar. 
En fin, me complica mucho la situación de Sebastián y francamente estoy confundido. Y yo que estaba tan contento por el examen de matemáticas. Ahora estoy metido en un lío. Este periodo de exámenes no lo olvidaré fácilmente. Realmente no sé qué hacer. Me siento muy angustiado.” 
"""



def safe_parse_json(response_text):
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        cleaned_text = response_text.strip()
        if cleaned_text.startswith("{") and cleaned_text.endswith("}"):
            cleaned_text = cleaned_text
        else:
            cleaned_text = cleaned_text[cleaned_text.find("{"):cleaned_text.rfind("}") + 1]

        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            print("Error al limpiar el JSON:", e)
            return None


def evaluate_and_respond(messages):
    context = "\n".join([f"{msg['user_name']}: {msg['message']}" for msg in messages[-5:]])
    
    full_prompt = f"""
Tienes la tarea de moderar una discusión sobre ética profesional según estas reglas:

### Tareas del Moderador:
1. Intervén **solo si es necesario** para promover el debate o mantenerlo dentro del tema.
2. **Ignora saludos, comentarios triviales y discusiones fluidas.**
3. Intervén solo si los usuarios:
   - Muestran confusión explícita.
   - Se desvían completamente del tema ético.
   - Hacen una pregunta directa al bot.
   - Si ves que hay consenso, introduce preguntas haciendo de abogado del diablo de la postura contraria a la que están de acuerdo.

### Discusión reciente:
{context}

### Caso Ético:
{caso_etico}

### Respuesta esperada:
Devuelve un JSON con la estructura exacta:
{{
    "should_react": true o false, // Si el bot debe responder o no.
    "response": "Texto breve de la respuesta del bot. Si no debe responder, este campo queda vacío."
}}
"""
    try:
        response = llm.predict(full_prompt)
        print(response)
        if not response:
            logging.error("Respuesta del LLM vacía.")
            return {"should_react": False, "response": ""}
        
        parsed_json = safe_parse_json(response)
        if parsed_json is None or not isinstance(parsed_json, dict):
            logging.error("Error al procesar el JSON.")
            return {"should_react": False, "response": ""}
        
        return parsed_json
    except Exception as error:
        logging.exception("Error al procesar la respuesta del LLM.")
        return {"should_react": False, "response": ""}

