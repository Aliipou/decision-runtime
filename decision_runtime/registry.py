"""Agent registry — who is known to the runtime. Thread-safe.

Registering an agent binds an `agent_id` to a kernel `actor`. This is admission
(identity), not authority: being registered lets an agent *submit* actions; it
never lets the agent *authorize* one.
"""

from __future__ import annotations

import threading
import uuid

from .session import Session


class RegistryError(RuntimeError):
    pass


class AgentRegistry:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def register(self, actor: str, agent_id: str | None = None) -> Session:
        agent_id = agent_id or f"agent-{uuid.uuid4().hex[:8]}"
        with self._lock:
            if agent_id in self._sessions:
                raise RegistryError(f"agent_id already registered: {agent_id}")
            session = Session(session_id=agent_id, actor=actor)
            self._sessions[agent_id] = session
            return session

    def get(self, agent_id: str) -> Session:
        with self._lock:
            try:
                return self._sessions[agent_id]
            except KeyError:
                raise RegistryError(f"unknown agent: {agent_id}") from None

    def active(self) -> list[Session]:
        with self._lock:
            return [s for s in self._sessions.values() if s.can_act]

    def __len__(self) -> int:
        with self._lock:
            return len(self._sessions)
