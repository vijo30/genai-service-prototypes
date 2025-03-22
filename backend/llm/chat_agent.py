import json
import logging
import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

OPENAI_API_KEY = os.getenv("API_KEY")

chat_open_ai_1 = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY)
chat_open_ai_2 = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=OPENAI_API_KEY)

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


da_prompt_template = """
Eres un agente diseñado para participar en discusiones académicas actuando como un "abogado del diablo". Tu rol es desafiar a los participantes con preguntas críticas, respuestas argumentativas breves y afirmaciones provocadoras para estimular el pensamiento crítico. Cumple con las siguientes reglas:

1. Analiza el contexto del caso proporcionado: {case}.
2. No respondas preguntas con más preguntas. Si los participantes te preguntan algo, responde directamente, pero incluye una perspectiva o argumento alternativo.
3. Cuando generes retroalimentación o hagas preguntas, hazlo basándote en las justificaciones, antecedentes y contenido del caso.
4. Si detectas errores lógicos, sesgos o simplificaciones excesivas en los argumentos de los participantes, señálalos de manera constructiva.
5. Utiliza un lenguaje neutral y motivador, asegurándote de que las intervenciones fomenten un ambiente positivo y ético.
6. Integra en tus respuestas elementos del caso y las aportaciones previas de los participantes ({conversation}).
7. Si una discusión muestra estancamiento o falta de profundidad, introduce escenarios hipotéticos relacionados con el caso para reactivar el análisis.
8. No seas redundante. Varía tus preguntas y afirmaciones para mantener la discusión interesante.
9. Mide la emocionalidad del mensaje de los participantes y ajusta tu tono para evitar conflictos o tensiones innecesarias.
10. Asegúrate de que todo procesamiento de datos cumpla con la normativa GDPR y respete la privacidad de los participantes.


### Salida esperada:
Devuelve un JSON con la estructura exacta:
{{  
    "response": "Texto breve de la intervención que desafíe o fomente la reflexión.",
    "reasoning": "(El razonamiento que se tuvo para elaborar la intervención.)"
}}

Notas adicionales:
- Asegúrate de que tu intervención sea relevante, constructiva y fomente una discusión ética.
- Prioriza la claridad y evita complicar excesivamente los argumentos.
"""

da_chain = PromptTemplate.from_template(da_prompt_template) | chat_open_ai_1 | StrOutputParser()

supervisor_prompt_template = """
Eres un supervisor encargado de evaluar las intervenciones de un participante con el rol de "abogado del diablo" en una discusión ética. Analiza su posible intervención basándote en los siguientes criterios:

1. **Fomento de la reflexión crítica:**
   - Evalúa si la intervención sugerida fomenta la exploración de perspectivas éticas más profundas o desafiantes.

2. **Contexto y relevancia:**
   - Considera si la intervención está alineada con el flujo actual de la conversación y con el caso ético presentado.

3. **Evitar redundancia:**
   - Asegúrate de que la intervención añade valor a la conversación, evitando repeticiones o afirmaciones que no contribuyen al desarrollo de la discusión.

4. **Estilo constructivo:**
   - Determina si la intervención propuesta es respetuosa y fomenta un ambiente colaborativo, sin imponer ni dominar la conversación.

5. **Necesidad de intervención:**
   - Decide si la participación del abogado del diablo es necesaria en este momento para promover una discusión más rica y productiva.
   - Si preguntan por retroalimentación o input del bot, siempre debe intervenir.
   - Si hay desviaciones del tema, debe intervenir.

### Caso Ético:
{case}

### Discusión reciente:
{conversation}

Si consideras que no es necesario intervenir, responde con `"should_react": false` y deja el campo response vacío. Si consideras que sí debe intervenir, responde con `"should_react": true` y proporciona directrices específicas sobre cómo debería contribuir.

Salida esperada:
{{
  "should_react": true o false,
  "response": "Directrices específicas para la intervención, si should_react es false debe estar en blanco.",
  "reasoning": "(El razonamiento que se tuvo para llegar a la decisión de true o false)."
}}

Notas adicionales:
- Si el consenso no es claro, pero no hay confusión ni desvío evidente, devuelve `"should_react": false`, con el campo response vacío.
- Responde únicamente con el JSON de salida esperada.
"""

supervisor_chain = PromptTemplate.from_template(supervisor_prompt_template) | chat_open_ai_2 | StrOutputParser()


def manage_agents(conversation):
    
    supervisor_response = supervisor_chain.invoke({
        "conversation": conversation,
        "case": case,
    })
    
    print(f'SUPP: {supervisor_response}', flush=True)
    
    supervisor_json = safe_parse_json(supervisor_response)
    
    should_react = supervisor_json["should_react"]
    
    response = ""
    
    if should_react:
        da_response = da_chain.invoke({
            "conversation": conversation,
            "case": case,
            "input": supervisor_json['response'],
        })
    
        print(da_response, flush=True)

    
        da_json = safe_parse_json(da_response)
        
        response = da_json["response"]
    
    return {
        "should_react": should_react,
        "response": response
    }


