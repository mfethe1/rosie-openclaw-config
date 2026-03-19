import unittest
import json
import subprocess
from unittest.mock import patch, MagicMock

# Import the module to test
import model_health_check

class TestModelHealthCheck(unittest.TestCase):

    @patch('subprocess.run')
    def test_health_check_api_unreachable(self, mock_run):
        # Simulate API reachability check returning 500
        mock_reachability = MagicMock()
        mock_reachability.stdout = b'500\n'
        mock_run.return_value = mock_reachability
        
        result = model_health_check.health_check()
        
        self.assertFalse(result['pass'])
        self.assertEqual(result['primary_failures'], len(model_health_check.MODELS))
        self.assertEqual(result['note'], 'OpenRouter API unreachable')
        for model in model_health_check.MODELS:
            self.assertEqual(result['results'][model], 'unreachable')

    @patch('subprocess.run')
    def test_health_check_api_timeout(self, mock_run):
        # Simulate timeout on the curl command
        mock_run.side_effect = subprocess.TimeoutExpired(cmd='curl', timeout=10)
        
        result = model_health_check.health_check()
        
        self.assertFalse(result['pass'])
        self.assertEqual(result['note'], 'OpenRouter API unreachable')

    @patch('subprocess.run')
    def test_health_check_all_healthy(self, mock_run):
        # Setup mock returns: first call (reachability) returns 200, second call (fetch) returns models
        mock_reachability = MagicMock()
        mock_reachability.stdout = b'200\n'
        
        mock_fetch = MagicMock()
        mock_models = {"data": [{"id": m} for m in model_health_check.MODELS]}
        mock_fetch.stdout = json.dumps(mock_models).encode()
        
        mock_run.side_effect = [mock_reachability, mock_fetch]
        
        result = model_health_check.health_check()
        
        self.assertTrue(result['pass'])
        self.assertEqual(result['primary_failures'], 0)
        self.assertEqual(result['note'], 'OpenRouter API reachable')
        for model in model_health_check.MODELS:
            self.assertEqual(result['results'][model], 'healthy')

    @patch('subprocess.run')
    def test_health_check_models_not_listed(self, mock_run):
        # Setup mock returns: first call (reachability) returns 200, second call returns an empty models list
        mock_reachability = MagicMock()
        mock_reachability.stdout = b'200\n'
        
        mock_fetch = MagicMock()
        mock_models = {"data": [{"id": "some_other_model"}]}
        mock_fetch.stdout = json.dumps(mock_models).encode()
        
        mock_run.side_effect = [mock_reachability, mock_fetch]
        
        result = model_health_check.health_check()
        
        self.assertTrue(result['pass'])  # Pass is still True since API is reachable
        for model in model_health_check.MODELS:
            self.assertEqual(result['results'][model], 'not_listed')

if __name__ == '__main__':
    unittest.main()
