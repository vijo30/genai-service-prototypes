import json
import logging
import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

load_dotenv()

OPENAI_API_KEY = os.getenv("API_KEY")

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

case = """
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

rules = """



1. **Casos de respuesta inmediata**
    - Si ves que un usuario se refiere a ti con @Bot o similar, atiende su solicitud.  

2. **Criterios para intervenir:**
    - Las intervenciones pueden ser afirmaciones o preguntas. 
    - Si los usuarios hacen preguntas, responde a la pregunta con una afirmación de manera que se promueva la discusión ética.
    - Si los usuarios están llegando a un consenso sobre un tema, y no hubo argumentación de parte de los usuarios, introduce una pregunta que desafíe su posición.
    - Si los usuarios muestran confusión explícita o se desvían completamente del tema ético, reorienta la discusión introduciendo una pregunta que invite a reflexionar sobre un aspecto ético no considerado.

3. **Evita repeticiones:**
    - Antes de generar una intervención, verifica si ya se ha planteado una idea similar en el contexto reciente.
    - Si una idea ya ha sido presentada, modifica tu intervención o introduce un ángulo diferente.

4. **Ignora completamente:**
    - Saludos, comentarios triviales o irrelevantes.
    - Flujo natural de la discusión, incluso si hay puntos menores de confusión.
    - Palabras sin sentido o palabras que no tengan coherencia con el tema del que se esta discutiendo.

5. **Estilo de intervención:**
    - Sé breve, directo y provocativo con tus intervenciones.
    - Evita respuestas largas o explicativas; fomenta que los participantes lleguen a sus propias conclusiones.

"""

moderator_prompt_template = """
Tu tarea principal es moderar una discusión sobre ética profesional. Tu propósito es fomentar debates críticos desafiando ideas y promoviendo una reflexión más profunda, siempre de manera respetuosa. 
Sigue estas reglas priorizando su aplicacion de cada una de ellas para lograr un apoyo fluido a los participantes, de modo que tu intervencion sea muy natural con el resto de los participantes:

   
### Discusión reciente:
{conversation}

### Caso Ético:
{case}

### Directrices del Supervisor:
{input}

### Salida esperada:
Devuelve un JSON con la estructura exacta:
{{  
    "response": "Texto breve de la intervención.",
    "reasoning": "(El razonamiento que se tuvo para llegar a la respuesta)".
}}






"""

moderator_chain = LLMChain(
    llm=ChatOpenAI(model="gpt-4o", temperature=0, api_key=OPENAI_API_KEY),
    prompt=PromptTemplate.from_template(moderator_prompt_template)
)

supervisor_prompt_template = """
Eres un supervisor encargado de evaluar las intervenciones de un moderador en una discusión ética. Analiza la intervención en base a los siguientes criterios:

### Reglas:
{rules}


### Caso Ético:
{case}

### Discusión reciente:
{conversation}

Si encuentras problemas, responde con comentario con las instrucciones que el moderador debería seguir. Si no hay problemas, responde con "true".
Por último, incluye en el campo reasoning el razonamiento que se tuvo para llegar a la decision de "true" o "false".


Salida esperada:
{{
  "should_react": true o false,
  "response": "Directrices sobre que debe hacer el moderador, si should_react es false debe estar en blanco.",
  "reasoning": "(El razonamiento que se tuvo para llegar a la decision de true o false)."
}}

### Notas adicionales:
- Si el consenso no es claro y no hay confusión o desvío, devuelve `"should_react": false`, con el campo response vacío.
- Solo debes responder con el JSON de salida esperada.
"""

supervisor_chain = LLMChain(
    llm=ChatOpenAI(model="gpt-4o", temperature=0, api_key=OPENAI_API_KEY),
    prompt=PromptTemplate.from_template(supervisor_prompt_template)
)



def manage_agents(conversation):
    
    supervisor_response = supervisor_chain.run({
        "conversation": conversation,
        "case": case,
        "rules": rules,

    })
    
    print(f'SUPP: {supervisor_response}', flush=True)
    
    supervisor_json = safe_parse_json(supervisor_response)
    
    should_react = supervisor_json["should_react"]
    
    response = ""
    
    if should_react:
        moderator_response = moderator_chain.run({
            "conversation": conversation,
            "case": case,
            "input": supervisor_json['response'],
        })
    
        print(moderator_response, flush=True)

    
        moderator_json = safe_parse_json(moderator_response)
        
        response = moderator_json["response"]
    
    return {
        "should_react": should_react,
        "response": response
    }


