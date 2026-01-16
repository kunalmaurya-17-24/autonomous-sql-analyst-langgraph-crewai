
import time
import logging

logger = logging.getLogger(__name__)

class GlobalRateLimiter:
    _instance = None
    _count = 0
    _threshold = 4
    _pause_duration = 60

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalRateLimiter, cls).__new__(cls)
        return cls._instance

    @classmethod
    def check_and_wait(cls):
        cls._count += 1
        logger.info(f"API Call Count: {cls._count}/{cls._threshold}")
        if cls._count >= cls._threshold:
            logger.warning(f"Rate limit threshold ({cls._threshold}) reached. Pausing for {cls._pause_duration} seconds...")
            print(f"\n⚠️ Rate limit hit. Pausing for {cls._pause_duration}s to respect free tier... ⚠️\n")
            time.sleep(cls._pause_duration)
            cls._count = 0
            logger.info("Resuming execution.")

# Global instance
rate_limiter = GlobalRateLimiter()
