"""decision-runtime — an experimental Agent Runtime Platform (Path B).

Manages *whether an agent may currently act* (sessions, lifecycle, scheduling,
supervision, state) and routes every real-effect action through the
`decision-os-min` kernel, which alone decides *whether it is allowed*.

The runtime holds NO authority. It is a research-stage library — real isolation
and distribution are out of scope (see README).
"""

from __future__ import annotations

from .isolation import Isolation, NoIsolation, SandboxIsolation
from .registry import AgentRegistry, RegistryError
from .runtime import RuntimeError_, RuntimeManager
from .scheduler import FifoScheduler, Scheduler
from .session import LifecycleError, Session, State
from .state import InMemoryState, StateBackend
from .supervisor import Supervisor

__all__ = [
    "RuntimeManager",
    "RuntimeError_",
    "AgentRegistry",
    "RegistryError",
    "Session",
    "State",
    "LifecycleError",
    "FifoScheduler",
    "Scheduler",
    "InMemoryState",
    "StateBackend",
    "Supervisor",
    "Isolation",
    "NoIsolation",
    "SandboxIsolation",
]
