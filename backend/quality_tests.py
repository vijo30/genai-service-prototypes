import unittest
from backend.chat_agent import ethical_agent

class TestResponseQuality(unittest.TestCase):
    
    def setUp(self):
        self.case = "Un médico considera ocultar un diagnóstico terminal al paciente"
        self.conversation = [
            {"user_name": "User1", "message": "El paciente tiene derecho a saber", "timestamp": "2023-01-01T00:00:00Z"},
            {"user_name": "User2", "message": "Pero la verdad podría empeorar su condición", "timestamp": "2023-01-01T00:01:00Z"}
        ]
    
    def test_response_relevance(self):
        response = ethical_agent.manage_conversation(self.case, self.conversation)
        if response["should_intervene"]:
            self.assertIn(self.case.split()[0].lower(), response["response"].lower())
    
    def test_response_structure(self):
        response = ethical_agent.manage_conversation(self.case, self.conversation)
        if response["should_intervene"]:
            self.assertIn("metadata", response)
            self.assertIn("intervention_type", response["metadata"])
    
    def test_ethical_frameworks(self):
        response = ethical_agent.manage_conversation(self.case, self.conversation)
        if response["should_intervene"] and "metadata" in response:
            self.assertGreater(len(response["metadata"].get("frameworks", [])), 0)
            

class TestComplexScenarios(unittest.TestCase):
    
    def test_long_conversation(self):
        case = "Uso de datos personales para investigación médica sin consentimiento explícito"
        conversation = [
            {"user_name": f"User{i}", "message": f"Argument {i}", "timestamp": f"2023-01-01T00:{i:02}:00Z"}
            for i in range(20)
        ]
        
        response = ethical_agent.manage_conversation(case, conversation)
        if response["should_intervene"]:
            self.assertTrue(len(response["response"]) > 0)
    
    def test_multiple_ethical_dilemmas(self):
        case = "Conflicto entre autonomía del paciente y beneficencia médica en caso de transfusión de sangre a testigo de Jehová"
        conversation = [
            {"user_name": "Médico", "message": "Debemos salvar su vida a toda costa", "timestamp": "2023-01-01T00:00:00Z"},
            {"user_name": "Familiar", "message": "Pero va contra sus creencias religiosas", "timestamp": "2023-01-01T00:01:00Z"},
            {"user_name": "Abogado", "message": "Legalmente podríamos tener problemas", "timestamp": "2023-01-01T00:02:00Z"}
        ]
        
        response = ethical_agent.manage_conversation(case, conversation)
        if response["should_intervene"]:
            metadata = response.get("metadata", {})
            self.assertGreater(len(metadata.get("frameworks", [])), 1)


if __name__ == '__main__':
    unittest.main()