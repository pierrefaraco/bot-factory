from threading import Lock
from functools import wraps


def singleton(cls):
    """
    Singleton decorator that ensures only one instance of a class is created.
    Thread-safe implementation using a double-checked locking pattern.

    Usage:
        @singleton
        class MyService:
            def __init__(self):
                pass

        # Both calls return the same instance
        service1 = MyService()
        service2 = MyService()
        assert service1 is service2

    Args:
        cls: The class to make singleton

    Returns:
        A decorator function that returns the singleton instance
    """
    _instances = {}
    _lock = Lock()

    @wraps(cls)
    def get_instance(*args, **kwargs):
        if cls not in _instances:
            with _lock:
                # Double-checked locking pattern
                if cls not in _instances:
                    _instances[cls] = cls(*args, **kwargs)
        return _instances[cls]

    # Add a method to clear instance for testing purposes
    get_instance.clear_instance = lambda: _instances.pop(cls, None)

    return get_instance
