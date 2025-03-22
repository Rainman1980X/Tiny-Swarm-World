import os
import inspect
import importlib
import pkgutil

class InfraCoreContainer:
    _instance = None  # Singleton instance

    def __new__(cls):
        """Ensures only one instance of the container exists (Singleton)"""
        if cls._instance is None:
            cls._instance = super(InfraCoreContainer, cls).__new__(cls)
            cls._instance.services = {}  # Storage for all registered services
            cls._instance.root_module = cls.find_root_module()  # Root of the project
        return cls._instance

    def register(self, class_type, instance=None):
        """
        Registers a class or a specific instance.
        If instance is provided, it's stored immediately.
        Otherwise, the class type itself is stored for lazy instantiation.
        """
        if instance:
            self.services[class_type] = instance
        else:
            self.services[class_type] = class_type

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
                               ["_is_component", "_is_service", "_is_repository", "_is_singleton"]):
                            self.register(obj)
        except ModuleNotFoundError:
            print(f"[WARNING] Could not scan module: {module_name}")

    @staticmethod
    def find_root_module():
        """Finds the root module using PathNormalizer and os.getcwd()"""
        root_path = os.path.basename(os.path.abspath(os.getcwd()))
        return os.path.basename(root_path)  # Converts path to module name

# Global instance
infra_core_container = InfraCoreContainer()
