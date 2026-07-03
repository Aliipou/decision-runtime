"""Agent memory / context — data an agent carries across actions. Thread-safe.

Hard rule (Phase-3 mistake #7): **memory can never change what the kernel
decides.** It is a per-agent append-only context buffer, nothing more. Policy is
not stored here and is never read from here.
"""

from __future__ import annotations

import threading
from collections import defaultdict, deque
from typing import Any


class ContextMemory:
    def __init__(self, max_items: int = 1000) -> None:
        self._buf: dict[str, deque[Any]] = defaultdict(lambda: deque(maxlen=max_items))
        self._lock = threading.Lock()

    def append(self, agent_id: str, item: Any) -> None:
        with self._lock:
            self._buf[agent_id].append(item)

    def recent(self, agent_id: str, n: int = 10) -> list[Any]:
        with self._lock:
            return list(self._buf.get(agent_id, ()))[-n:]

    def clear(self, agent_id: str) -> None:
        with self._lock:
            self._buf.pop(agent_id, None)
