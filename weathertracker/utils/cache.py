import threading
import time
from collections import OrderedDict


class TTLCache:
    """Thread-safe in-memory cache with per-key TTL, LRU eviction."""

    def __init__(self, ttl_seconds: int = 300, maxsize: int = 256):
        self._ttl = ttl_seconds
        self._maxsize = maxsize
        self._data = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key) -> object | None:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            value, expires_at = item
            if time.monotonic() > expires_at:
                del self._data[key]
                return None
            self._data.move_to_end(key)
            return value

    def set(self, key, value, ttl_seconds: int | None = None) -> None:
        with self._lock:
            ttl = ttl_seconds or self._ttl
            self._data[key] = (value, time.monotonic() + ttl)
            self._data.move_to_end(key)
            while len(self._data) > self._maxsize:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()