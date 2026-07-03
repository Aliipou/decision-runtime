"""Agent sessions and their lifecycle — the part of "runtime" that is REAL here.

A session is an agent's live presence in the runtime: it has an id, a bound
`actor` (its kernel identity), a state, and a history. Nothing here decides
anything — a session only tracks *whether an agent may currently act*, never
*whether an action is allowed* (that is the kernel's job).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class State(StrEnum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"


# Allowed transitions. Anything not here is rejected — a small, explicit state
# machine, not implicit flags.
_TRANSITIONS = {
    State.CREATED: {State.RUNNING, State.TERMINATED},
    State.RUNNING: {State.SUSPENDED, State.TERMINATED},
    State.SUSPENDED: {State.RUNNING, State.TERMINATED},
    State.TERMINATED: set(),
}


class LifecycleError(RuntimeError):
    pass


@dataclass
class Session:
    session_id: str
    actor: str                       # the kernel identity every action is bound to
    state: State = State.CREATED
    restarts: int = 0
    history: list[str] = field(default_factory=list)

    def _to(self, target: State) -> None:
        if target not in _TRANSITIONS[self.state]:
            raise LifecycleError(f"illegal transition {self.state.value} -> {target.value}")
        self.history.append(f"{self.state.value}->{target.value}")
        self.state = target

    def start(self) -> None:
        self._to(State.RUNNING)

    def suspend(self) -> None:
        self._to(State.SUSPENDED)

    def resume(self) -> None:
        if self.state is not State.SUSPENDED:
            raise LifecycleError(f"cannot resume from {self.state.value}")
        self._to(State.RUNNING)

    def terminate(self) -> None:
        self._to(State.TERMINATED)

    @property
    def can_act(self) -> bool:
        return self.state is State.RUNNING
