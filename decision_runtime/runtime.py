"""RuntimeManager — the Agent Runtime Platform's core. REAL integration.

It manages *whether an agent may currently act* (sessions, lifecycle, scheduling,
supervision) and routes every real-effect action **through the decision-os-min
kernel**, which alone decides *whether the action is allowed*.

The unbreakable invariant: **the runtime holds no authority.** It owns no signing
key, constructs no decision, mints no token. If it is asked to run something the
kernel denied, it cannot — because it can only carry out a kernel-signed decision
via the kernel's own executor.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from decision_os_min import DecisionOS, Outcome

from .isolation import Isolation, NoIsolation
from .registry import AgentRegistry
from .scheduler import FifoScheduler, Scheduler
from .session import Session
from .state import InMemoryState, StateBackend
from .supervisor import Supervisor


class RuntimeError_(RuntimeError):
    """Runtime-level (operational) error — distinct from a security refusal, which
    surfaces as a non-executed Outcome from the kernel."""


class RuntimeManager:
    def __init__(
        self,
        policy: dict[str, Any],
        *,
        audit_path: str,
        tools: dict[str, Callable[[dict[str, Any]], Any]],
        isolation: Isolation | None = None,
        supervisor: Supervisor | None = None,
        scheduler: Scheduler | None = None,
        state: StateBackend | None = None,
    ) -> None:
        # The kernel (via decision-os-min) is the SOLE authority + the audit truth.
        self._dos = DecisionOS(policy, audit_path=audit_path)
        self.registry = AgentRegistry()
        self.scheduler: Scheduler = scheduler or FifoScheduler()
        self.state: StateBackend = state or InMemoryState()
        self.supervisor = supervisor or Supervisor()
        self.isolation: Isolation = isolation or NoIsolation()
        self._tools = tools

    @property
    def kernel_public_key(self) -> str:
        return self._dos.kernel.public_key_hex()

    def spawn(self, actor: str, agent_id: str | None = None) -> Session:
        """Register an agent and start its session (CREATED -> RUNNING)."""
        session = self.registry.register(actor, agent_id)
        session.start()
        return session

    def submit(self, agent_id: str, action: dict[str, Any]) -> Outcome:
        """Route one action through the kernel. Raises RuntimeError_ only for
        *operational* problems (agent not runnable); a security DENY comes back as
        an Outcome with executed=False, not an exception."""
        session = self.registry.get(agent_id)
        if not session.can_act:
            raise RuntimeError_(f"agent '{agent_id}' cannot act (state={session.state.value})")

        # Bind the actor to the SESSION identity — an agent cannot spoof another
        # actor by putting a different 'actor' in its action. Admission binds
        # identity; the kernel still decides authority.
        bound = {**action, "actor": session.actor}

        # Effects run through the isolation boundary (default: none). The kernel's
        # executor still gates which tool runs, and on what payload.
        wrapped = {
            name: (lambda p, f=fn: self.isolation.run(f, p)) for name, fn in self._tools.items()
        }
        return self._dos.handle(bound, wrapped)

    def enqueue(self, agent_id: str, action: dict[str, Any]) -> None:
        self.scheduler.enqueue((agent_id, action))

    def run_pending(self) -> list[Outcome]:
        """Drain the scheduler in order, routing each through the kernel."""
        outcomes: list[Outcome] = []
        while len(self.scheduler):
            item = self.scheduler.dequeue()
            if item is None:
                break
            agent_id, action = item
            outcomes.append(self.submit(agent_id, action))
        return outcomes
