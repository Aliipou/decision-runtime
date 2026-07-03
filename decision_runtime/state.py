"""Per-agent state store. In-memory reference implementation + a Protocol so a
durable backend (Redis, SQLite, …) can be dropped in later. REAL, minimal.

State is data an agent carries across actions — it is NOT policy and can never
change what the kernel decides (Phase-3 mistake #7).
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class StateBackend(Protocol):
    def get(self, agent_id: str, key: str) -> Any | None: ...
    def set(self, agent_id: str, key: str, value: Any) -> None: ...
    def clear(self, agent_id: str) -> None: ...


class InMemoryState:
    def __init__(self) -> None:
        self._d: dict[str, dict[str, Any]] = {}

    def get(self, agent_id: str, key: str) -> Any | None:
        return self._d.get(agent_id, {}).get(key)

    def set(self, agent_id: str, key: str, value: Any) -> None:
        self._d.setdefault(agent_id, {})[key] = value

    def clear(self, agent_id: str) -> None:
        self._d.pop(agent_id, None)
