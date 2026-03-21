import unittest
from unittest.mock import patch, mock_open
import requests

from winnie_proactive_health import health_check, MODELS, THRESHOLD_LATENCY_MS

class TestWinnieProactiveHealth(unittest.TestCase):

    @patch('winnie_proactive_health.time.time')
    @patch('builtins.open', new_callable=mock_open)
    def test_health_check_healthy(self, mock_file, mock_time):
        mock_time.side_effect = [100.0, 101.0] * len(MODELS)
        
        results = health_check()
        
        self.assertEqual(len(results['models']), len(MODELS))
        for model in MODELS:
            self.assertEqual(results['models'][model]['status'], 'healthy')
            self.assertEqual(results['models'][model]['latency_ms'], 1000.0)
            self.assertFalse(results['models'][model]['alert'])

    @patch('winnie_proactive_health.time.time')
    @patch('builtins.open', new_callable=mock_open)
    def test_health_check_high_latency(self, mock_file, mock_time):
        mock_time.side_effect = [100.0, 104.0] * len(MODELS)
        
        results = health_check()
        
        for model in MODELS:
            self.assertEqual(results['models'][model]['status'], 'healthy')
            self.assertEqual(results['models'][model]['latency_ms'], 4000.0)
            self.assertTrue(results['models'][model]['alert'])

    @patch('winnie_proactive_health.time.time')
    @patch('winnie_proactive_health.time.sleep')
    @patch('builtins.open', new_callable=mock_open)
    def test_health_check_exception_failure(self, mock_file, mock_sleep, mock_time):
        mock_time.side_effect = requests.RequestException("Connection error")
        
        results = health_check()
        
        for model in MODELS:
            self.assertEqual(results['models'][model]['status'], 'failed')
            self.assertIn('Connection error', results['models'][model]['error'])

    @patch('winnie_proactive_health.time.time')
    @patch('winnie_proactive_health.time.sleep')
    @patch('builtins.open', new_callable=mock_open)
    def test_health_check_exception_retry_success(self, mock_file, mock_sleep, mock_time):
        side_effects = []
        for _ in MODELS:
            side_effects.append(requests.RequestException("Error"))
            side_effects.extend([100.0, 102.0])
            
        mock_time.side_effect = side_effects
        
        results = health_check()
        
        for model in MODELS:
            self.assertEqual(results['models'][model]['status'], 'healthy')
            self.assertEqual(results['models'][model]['latency_ms'], 2000.0)

if __name__ == '__main__':
    unittest.main()
