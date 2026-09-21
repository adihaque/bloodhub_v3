from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class MapProvider(ABC):
    @abstractmethod
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        pass

    @abstractmethod
    def geocode(self, query: str) -> Optional[Dict[str, Any]]:
        pass
