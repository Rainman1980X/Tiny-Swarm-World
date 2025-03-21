import inspect
import threading

from infrastructure.dependency_injection.infra_core_di_container import infra_core_container

# Storage for singleton instances
_singleton_instances = {}
_singleton_lock = threading.Lock()  # Lock for thread safety


def singleton(cls):
    """Ensures that a class is only instantiated once (Thread-Safe Singleton)."""

    def get_instance(*args, **kwargs):
        if cls not in _singleton_instances:
            with _singleton_lock:  # Prevents race conditions in multithreaded environments
                if cls not in _singleton_instances:  # Double-Checked Locking
                    _singleton_instances[cls] = cls(*args, **kwargs)
        return _singleton_instances[cls]

    cls.get_instance = get_instance  # Optional: Allows manual access to the singleton instance
    infra_core_container.register(cls,get_instance())  # Automatically register in DI container
    return get_instance  # Returns the singleton instance

def component(cls):
    """Marks a class as a generic component for Dependency Injection"""
    cls._is_component = True
    infra_core_container.register(cls)
    return cls

def service(cls):
    """Marks a class as a service that can be injected"""
    cls._is_service = True
    infra_core_container.register(cls)
    return cls

def repository(cls):
    """Marks a class as a repository for data access and storage"""
    cls._is_repository = True
    infra_core_container.register(cls)
    return cls

def inject(func):
    """Decorator for automatic dependency injection from the DI container."""
    def wrapper(*args, **kwargs):
        dependencies = {
            name: infra_core_container.resolve(param.annotation)
            for name, param in inspect.signature(func).parameters.items()
            if param.annotation in infra_core_container.services and name not in kwargs
        }
        return func(*args, **{**kwargs, **dependencies})
    return wrapper