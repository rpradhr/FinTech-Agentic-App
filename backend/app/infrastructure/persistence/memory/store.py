"""
Shared in-memory store used by all in-memory repositories.

All repositories in the same test or dev session share one InMemoryStore instance
so reads and writes are coherent across repository boundaries.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


class InMemoryStore:
    """Thread-unsafe, single-process key-value store partitioned by collection name."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, Any]] = defaultdict(dict)

    def put(self, collection: str, key: str, value: Any) -> None:
        self._data[collection][key] = value

    def get(self, collection: str, key: str) -> Any | None:
        return self._data[collection].get(key)

    def delete(self, collection: str, key: str) -> None:
        self._data[collection].pop(key, None)

    def all(self, collection: str) -> list[Any]:
        return list(self._data[collection].values())

    def filter(self, collection: str, **kwargs: Any) -> list[Any]:
        """Simple equality filter across all items in a collection."""
        results = []
        for item in self._data[collection].values():
            if all(getattr(item, k, None) == v for k, v in kwargs.items()):
                results.append(item)
        return results

    def clear(self) -> None:
        self._data.clear()
