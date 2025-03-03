from abc import ABC, abstractmethod
from typing import Optional

class ExtractionStrategy(ABC):
    """Abstrakte Basis für verschiedene Extraktionsstrategien."""

    @abstractmethod
    def extract(self, result) -> Optional[str]:
        """Extrahiert eine bestimmte Information aus dem Resultat."""
        pass
