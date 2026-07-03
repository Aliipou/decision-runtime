"""Inter-agent message passing (IPC). Thread-safe, in-memory.

Messages are **data**, never authority. An agent receiving a message still has to
submit any resulting action through the kernel like anything else — a message can
ask, it can never authorize. No message can carry a decision or a token.
"""

from __future__ import annotations

import threading
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Message:
    sender: str
    recipient: str
    body: Any


class MessageBus:
    def __init__(self) -> None:
        self._inbox: dict[str, deque[Message]] = defaultdict(deque)
        self._lock = threading.Lock()

    def send(self, sender: str, recipient: str, body: Any) -> None:
        with self._lock:
            self._inbox[recipient].append(Message(sender, recipient, body))

    def receive(self, agent_id: str) -> list[Message]:
        """Drain and return this agent's inbox."""
        with self._lock:
            box = self._inbox.get(agent_id)
            if not box:
                return []
            msgs = list(box)
            box.clear()
            return msgs

    def pending(self, agent_id: str) -> int:
        with self._lock:
            return len(self._inbox.get(agent_id, ()))
