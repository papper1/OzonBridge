import time
from functools import wraps

from utils.logger import get_logger


LOGGER = get_logger("utils.retry")


def retry(
    attempts: int = 3,
    delay: float = 1.0,
    exceptions: tuple = (Exception,),
):
    """Retry a function call when configured exceptions are raised."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt >= attempts:
                        raise
                    LOGGER.warning(
                        "Retry %s/%s for %s after error: %s",
                        attempt,
                        attempts,
                        func.__name__,
                        exc,
                    )
                    time.sleep(delay)

        return wrapper

    return decorator
