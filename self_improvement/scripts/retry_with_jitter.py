import time
import random
import functools
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def retry_with_jitter(max_retries=3, base_delay=1.0, max_delay=60.0, exceptions=(Exception,)):
    """
    Decorator for robust function execution with exponential backoff and jitter.
    
    Eliminates fragile hardcoded retry loops across the codebase.
    Applies 'Novel Solution Bias' to network/API instability.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"[{func.__name__}] Failed after {max_retries} retries: {e}")
                        raise
                    
                    # Exponential backoff with full jitter
                    temp_delay = min(max_delay, base_delay * (2 ** (retries - 1)))
                    delay = random.uniform(0, temp_delay)
                    
                    logger.warning(f"[{func.__name__}] Attempt {retries}/{max_retries} failed ({e}). Retrying in {delay:.2f}s...")
                    time.sleep(delay)
        return wrapper
    return decorator
