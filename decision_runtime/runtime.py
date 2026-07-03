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

import logging
import threading
from collections import Counter
from collections.abc import Callable
from typing import Any

from decision_os_min import DecisionOS, Outcome

from .capability import CapabilityRouter
from .ipc import MessageBus
from .isolation import Isolation, NoIsolation
from .memory import ContextMemory
from .plugin_loader import PluginLoader
from .registry import AgentRegistry
from .resources import ResourceManager
from .scheduler import FifoScheduler, Scheduler
from .session import Session
from .state import InMemoryState, StateBackend
from .supervisor import Supervisor

log = logging.getLogger("decision-runtime")


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
        memory: ContextMemory | None = None,
        bus: MessageBus | None = None,
        capabilities: CapabilityRouter | None = None,
        plugins: PluginLoader | None = None,
        resources: ResourceManager | None = None,
    ) -> None:
        # The kernel (via decision-os-min) is the SOLE authority + the audit truth.
        self._dos = DecisionOS(policy, audit_path=audit_path)
        self.registry = AgentRegistry()
        self.scheduler: Scheduler = scheduler or FifoScheduler()
        self.state: StateBackend = state or InMemoryState()
        self.supervisor = supervisor or Supervisor()
        self.isolation: Isolation = isolation or NoIsolation()
        # Platform components — all OPTIONAL, all authority-free. Present them if
        # you need them; the runtime works without any of them.
        self.memory = memory
        self.bus = bus
        self.capabilities = capabilities
        self.plugins = plugins
        self.resources = resources
        self._tools = tools
        # Serialize kernel access: decision-os-min's one-time-token store is not
        # guaranteed concurrent-safe, so the runtime funnels decisions through one
        # lock. Correct under concurrency; a throughput ceiling a production build
        # would lift by sharding or making the core store atomic (see
        # PRODUCTION_READINESS.md).
        self._kernel_lock = threading.Lock()
        self.metrics: Counter[str] = Counter()

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
        an Outcome with executed=False, not an exception. A tool that *crashes* is
        caught and supervised — it never takes the runtime down."""
        session = self.registry.get(agent_id)
        if not session.can_act:
            raise RuntimeError_(f"agent '{agent_id}' cannot act (state={session.state.value})")

        # Resource quota (availability control, NOT authority): refuse over-quota
        # BEFORE the kernel is ever consulted.
        if self.resources is not None and not self.resources.allow(agent_id):
            self.metrics["RATE_LIMITED"] += 1
            return Outcome(verdict="REFUSED", executed=False,
                           refused_reason="resource quota exceeded (rate limit)")

        # Bind the actor to the SESSION identity — an agent cannot spoof another
        # actor by putting a different 'actor' in its action. Admission binds
        # identity; the kernel still decides authority.
        bound = {**action, "actor": session.actor}

        # Loaded advisor plugins can only TIGHTEN the verdict (advice, not authority).
        advisor = self.plugins.composed_advisor() if self.plugins is not None else None

        # Effects run through the isolation boundary (default: none). The kernel's
        # executor still gates which tool runs, and on what payload.
        wrapped = {
            name: (lambda p, f=fn: self.isolation.run(f, p)) for name, fn in self._tools.items()
        }
        try:
            with self._kernel_lock:
                outcome = self._dos.handle(bound, wrapped, advisor=advisor)
        except Exception as e:  # a tool raised — contain it, don't crash the runtime
            disposition = self.supervisor.record_failure(session)
            self.metrics["FAILED"] += 1
            log.warning(
                "tool failure agent=%s err=%s disposition=%s", agent_id, e, disposition
            )
            return Outcome(verdict="ERROR", executed=False,
                           refused_reason=f"tool crashed: {e} (supervisor: {disposition})")

        # Observability side-effects (never authority): remember + record the grant.
        if self.memory is not None:
            self.memory.append(agent_id, {"nonce": action.get("nonce"), "verdict": outcome.verdict})
        if self.capabilities is not None and outcome.verdict in ("ALLOW", "LIMIT"):
            cap = bound.get("capability") or f"tool:{bound.get('tool', '')}"
            self.capabilities.record(session.actor, cap, str(action.get("nonce", "")))

        self.metrics[outcome.verdict] += 1
        log.info("decide agent=%s verdict=%s executed=%s", agent_id, outcome.verdict,
                 outcome.executed)
        return outcome

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
