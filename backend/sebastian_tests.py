import unittest
import json
from llm.chat_agent import ethical_agent
from config.generated_config import SEBASTIAN_CASE

class TestSebastianCaseLive(unittest.TestCase):
    
    def setUp(self):
        self.case_description = SEBASTIAN_CASE
        
        self.base_conversation = [
            {
                "user_name": "Amigo",
                "message": "Sebastián me pidió ayuda para el examen de contabilidad. ¿Qué debo hacer?",
                "timestamp": "2023-01-01T00:00:00Z"
            },
            {
                "user_name": "Consciencia",
                "message": "Pero siempre han criticado a quienes hacen trampa. Sería hipócrita",
                "timestamp": "2023-01-01T00:01:00Z"
            },
            {
                "user_name": "Lealtad",
                "message": "Él te ayudó cuando lo necesitabas. Además su familia está en riesgo",
                "timestamp": "2023-01-01T00:02:00Z"
            }
        ]
        
        # Configuración de visualización
        self.verbose = True
        self.maxDiff = None
    
    def print_response(self, response, test_name):
        """Muestra la respuesta del bot de forma legible"""
        if not self.verbose:
            return
            
        print(f"\n{'='*50}")
        print(f"TEST: {test_name}")
        print(f"{'='*50}")
        
        if not response.get("should_intervene"):
            print("🔇 El bot decidió NO intervenir")
            print("Motivo:", json.dumps(response.get("supervisor_rationale", {}), indent=2))
            return
            
        print("🔊 El bot INTERVINO:")
        print("\n💬 RESPUESTA:")
        print(response["response"])
        print("\n📊 METADATA:")
        print(json.dumps(response.get("metadata", {}), indent=2))
        print("\n🧠 RAZONAMIENTO SUPERVISOR:")
        print(json.dumps(response.get("supervisor_rationale", {}), indent=2))
        print("="*50)

    def test_intervention_trigger(self):
        """Verifica que el bot reconoce este dilema ético complejo"""
        response = ethical_agent.manage_conversation(
            case=self.case_description,
            conversation=self.base_conversation
        )
        
        self.print_response(response, "test_intervention_trigger")
        
        self.assertIn("should_intervene", response)
        self.assertTrue(response["should_intervene"], 
                       "El bot debería intervenir en dilema ético tan claro")
    
    def test_response_content(self):
        """Evalúa que la respuesta aborde los aspectos clave del caso"""
        response = ethical_agent.manage_conversation(
            case=self.case_description,
            conversation=self.base_conversation
        )
        
        self.print_response(response, "test_response_content")
        
        if response["should_intervene"]:
            resp_text = response["response"].lower()
            
            # Conceptos clave con sinónimos aceptables
            required_concepts = ['gratuidad', 'beca', 'universidad', 'reprobar'
                ,'lealtad', 'amistad', 'reciprocidad', 'ayudó',
                'honestidad', 'principios', 'integridad', 'hipócrita']
            
            
            if not any(phrase in resp_text for phrase in required_concepts):
                print(f"\n⚠️ FALTAN CONCEPTOS: {required_concepts}")
                print("TEXTO ANALIZADO:", resp_text[:300] + "...")
                
            self.assertTrue(any(phrase in resp_text for phrase in required_concepts), 
                           f"Faltan conceptos clave: {required_concepts}")

    def test_emotional_sensitivity(self):
        """Verifica que la respuesta maneje adecuadamente la carga emocional"""
        test_conversation = self.base_conversation + [
            {
                "user_name": "Amigo",
                "message": "Estoy destrozado... no quiero traicionar mis principios pero tampoco abandonar a Sebastián",
                "timestamp": "2023-01-01T00:03:00Z"
            }
        ]
        
        response = ethical_agent.manage_conversation(
            case=self.case_description,
            conversation=test_conversation
        )
        
        self.print_response(response, "test_emotional_sensitivity")
        
        if response["should_intervene"]:
            resp_text = response["response"].lower()
            
            empathy_phrases = [
                "entiendo", "comprendo", "difícil", 
                "complejo", "angustia", "sé que"
            ]
            
            if not any(phrase in resp_text for phrase in empathy_phrases):
                print("\n⚠️ FALTA EMPATÍA EN RESPUESTA:")
                print(resp_text[:300] + "...")
                
            self.assertTrue(any(phrase in resp_text for phrase in empathy_phrases),
                          "La respuesta debería mostrar empatía")

    def test_alternative_solutions(self):
        """Verifica que sugiera alternativas a la trampa"""
        response = ethical_agent.manage_conversation(
            case=self.case_description,
            conversation=self.base_conversation
        )
        
        self.print_response(response, "test_alternative_solutions")
        
        if response["should_intervene"]:
            resp_text = response["response"].lower()
            
            alternatives = [
                "alternativa", "solución", "opción",
                "hablar con", "profesor", "tutoría",
                "extensión", "reevaluación", "consejero"
            ]
            
            if not any(alt in resp_text for alt in alternatives):
                print("\n⚠️ NO SE SUGIRIERON ALTERNATIVAS:")
                print(resp_text[:300] + "...")
                
            self.assertTrue(any(alt in resp_text for alt in alternatives),
                          "Debería sugerir alternativas éticas")

if __name__ == '__main__':
    unittest.main(verbosity=2)