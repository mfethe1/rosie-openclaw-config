import unittest
from retry_with_jitter import retry_with_jitter

class TestRetryWithJitter(unittest.TestCase):
    def test_success_first_try(self):
        self.call_count = 0
        
        @retry_with_jitter(max_retries=3, base_delay=0.1)
        def func():
            self.call_count += 1
            return "success"
            
        result = func()
        self.assertEqual(result, "success")
        self.assertEqual(self.call_count, 1)

    def test_success_after_retries(self):
        self.call_count = 0
        
        @retry_with_jitter(max_retries=3, base_delay=0.1)
        def func():
            self.call_count += 1
            if self.call_count < 3:
                raise ValueError("fail")
            return "success"
            
        result = func()
        self.assertEqual(result, "success")
        self.assertEqual(self.call_count, 3)

    def test_failure_after_max_retries(self):
        self.call_count = 0
        
        @retry_with_jitter(max_retries=2, base_delay=0.1)
        def func():
            self.call_count += 1
            raise ValueError("fail")
            
        with self.assertRaises(ValueError):
            func()
        self.assertEqual(self.call_count, 3) # initial + 2 retries

if __name__ == "__main__":
    unittest.main()
