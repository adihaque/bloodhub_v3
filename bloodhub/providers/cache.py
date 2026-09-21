"""Optional cache abstraction. Local mode deliberately remains dependency-free."""
from abc import ABC, abstractmethod
from typing import Optional

class CacheProvider(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> bool:
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> bool:
        raise NotImplementedError

class MockCacheProvider(CacheProvider):
    def __init__(self):
        self._values = {}

    def get(self, key):
        return self._values.get(key)

    def set(self, key, value, ttl_seconds=None):
        self._values[key] = value
        return True

    def delete(self, key):
        return self._values.pop(key, None) is not None
