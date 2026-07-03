"""Scheduling — orders *when* work runs, NEVER *whether* it may.

A hard rule (Phase-3 mistake #6): the scheduler must not make security decisions.
It only decides order. Every dequeued item still passes through the kernel before
any effect. This module is a real FIFO plus a Protocol so a smarter policy can be
dropped in — without ever gaining authority.
"""

from __future__ import annotations

import threading
from collections import deque
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Scheduler(Protocol):
    def enqueue(self, item: Any) -> None: ...
    def dequeue(self) -> Any | None: ...
    def __len__(self) -> int: ...


class FifoScheduler:
    """First-in-first-out, thread-safe. Ordering only — no priority that could be
    abused as an implicit security signal."""

    def __init__(self) -> None:
        self._q: deque[Any] = deque()
        self._lock = threading.Lock()

    def enqueue(self, item: Any) -> None:
        with self._lock:
            self._q.append(item)

    def dequeue(self) -> Any | None:
        with self._lock:
            return self._q.popleft() if self._q else None

    def __len__(self) -> int:
        with self._lock:
            return len(self._q)
