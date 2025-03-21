import os
import inspect
import importlib
import pkgutil
from infrastructure.adapters.file_management.path_normalizer import PathNormalizer

class InfraCoreContainer:
    _instance = None  # Singleton instance

    def __new__(cls):
        """Ensures only one instance of the container exists (Singleton)"""
        if cls._instance is None:
            cls._instance = super(InfraCoreContainer, cls).__new__(cls)
            cls._instance.services = {}  # Storage for all registered services
            cls._instance.root_module = cls.find_root_module()  # Root of the project
        return cls._instance

    def register(self, class_type):
        """Registers a class type but does not instantiate it until needed."""
        self.services[class_type] = class_type  # Store the class reference

    def resolve(self, class_type):
        """Creates an instance with automatic dependency injection"""
        if class_type not in self.services:
            raise ValueError(f"Service {class_type.__name__} is not registered")

        constructor = inspect.signature(class_type.__init__)
        dependencies = {
            name: self.resolve(param.annotation)
            for name, param in constructor.parameters.items()
            if name != "self" and param.annotation in self.services
        }
        return class_type(**dependencies)  # Instantiate the class with resolved dependencies

    def scan_module(self, module_name):
        """Scans a module and registers all `@injectable`, `@Component`, `@Service`, and `@Repository` classes"""
        try:
            module = importlib.import_module(module_name)
            for _, name, ispkg in pkgutil.iter_modules(module.__path__):
                if not ispkg:  # Skip submodules
                    submodule = importlib.import_module(f"{module_name}.{name}")
                    for _, obj in inspect.getmembers(submodule, inspect.isclass):
                        if any(hasattr(obj, attr) for attr in
                               ["_is_component", "_is_service", "_is_repository"]):
                            self.register(obj)
        except ModuleNotFoundError:
            print(f"[WARNING] Could not scan module: {module_name}")

    @staticmethod
    def find_root_module():
        """Finds the root module using PathNormalizer and os.getcwd()"""
        root_path = PathNormalizer(os.getcwd()).normalize()
        return os.path.basename(root_path)  # Converts path to module name

# Global instance
infra_core_container = InfraCoreContainer()
