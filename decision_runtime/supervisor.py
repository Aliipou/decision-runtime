"""Supervision: failure tracking + a restart policy. REAL, minimal.

The supervisor decides whether a crashed agent is restarted or terminated. This is
an *operational* decision (availability), never a security one — it cannot
authorize actions, only keep agents alive within a bounded restart budget.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .session import Session, State


@dataclass
class Supervisor:
    max_restarts: int = 3
    _failures: dict[str, int] = field(default_factory=dict)

    def record_failure(self, session: Session) -> str:
        """Register a crash. Returns 'restart' or 'terminate' per the budget."""
        n = self._failures.get(session.session_id, 0) + 1
        self._failures[session.session_id] = n

        # Over budget, or already gone -> terminate (final).
        if n > self.max_restarts or session.state is State.TERMINATED:
            if session.state is not State.TERMINATED:
                session.terminate()
            return "terminate"

        # Restart: bring the session back to RUNNING via legal transitions.
        if session.state is State.CREATED:
            session.start()
        elif session.state is State.RUNNING:
            session.suspend()
            session.resume()
        elif session.state is State.SUSPENDED:
            session.resume()
        session.restarts += 1
        return "restart"

    def failures(self, session: Session) -> int:
        return self._failures.get(session.session_id, 0)
