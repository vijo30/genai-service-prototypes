import unittest
from unittest.mock import patch, MagicMock
from llm.chat_agent import EthicalDebateAgent
import json


class TestEthicalDebateAgent(unittest.TestCase):
    
    def setUp(self):
        self.agent = EthicalDebateAgent()
        self.sample_case = "Un paciente con cáncer terminal solicita ayuda para morir"
        self.sample_conversation = [
            {"user_name": "Usuario1", "message": "Creo que la eutanasia debería ser permitida", "timestamp": "2023-01-01T00:00:00Z"},
            {"user_name": "Usuario2", "message": "Pero va contra la ética médica", "timestamp": "2023-01-01T00:01:00Z"}
        ]
    
    def test_initialization_chatgpt(self):
        with patch.dict('os.environ', {'LLM_NAME': 'ChatGPT', 'API_KEY': 'test_key'}):
            agent = EthicalDebateAgent()
            self.assertIsNotNone(agent.chat_ai_1)
            self.assertIsNotNone(agent.chat_ai_2)
    
    def test_initialization_gemini(self):
        with patch.dict('os.environ', {'LLM_NAME': 'Gemini', 'API_KEY': 'test_key'}):
            agent = EthicalDebateAgent()
            self.assertIsNotNone(agent.chat_ai_1)
            self.assertIsNotNone(agent.chat_ai_2)
    
    def test_invalid_llm_config(self):
        with patch.dict('os.environ', {'LLM_NAME': 'Invalid', 'API_KEY': 'test_key'}):
            with self.assertRaises(ValueError):
                EthicalDebateAgent()
    
    
    def test_safe_parse_json_valid(self):
        valid_json = '{"key": "value"}'
        result = self.agent.safe_parse_json(valid_json)
        self.assertEqual(result, {"key": "value"})
    
    def test_safe_parse_json_invalid(self):
        invalid_json = 'not a json'
        result = self.agent.safe_parse_json(invalid_json)
        self.assertIsNone(result)
    
    def test_safe_parse_json_partial(self):
        partial_json = 'Text before {"key": "value"} text after'
        result = self.agent.safe_parse_json(partial_json)
        self.assertEqual(result, {"key": "value"})

if __name__ == '__main__':
    unittest.main()