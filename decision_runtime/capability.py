"""Capability router — OBSERVES the capabilities the kernel grants. NO authority.

This is the trap the name invites, so it's worth stating flatly: a capability
manager here does **not** grant capabilities. The kernel grants (by minting a
signed token on a permitting decision); this component only *records* what the
kernel already decided, so an operator can see and reason about who holds what.

It never authorizes, never mints, never overrides. It is a read-mostly ledger for
observability and (future) revocation signalling — a view over the kernel's
decisions, not a second source of them.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class Grant:
    actor: str
    capability: str
    token_id: str


class CapabilityRouter:
    def __init__(self) -> None:
        self._by_actor: dict[str, list[Grant]] = defaultdict(list)
        self._lock = threading.Lock()

    def record(self, actor: str, capability: str, token_id: str) -> None:
        """Record a grant the KERNEL issued (call after a permitting decision)."""
        with self._lock:
            self._by_actor[actor].append(Grant(actor, capability, token_id))

    def held_by(self, actor: str) -> list[Grant]:
        with self._lock:
            return list(self._by_actor.get(actor, ()))

    def count(self, actor: str) -> int:
        with self._lock:
            return len(self._by_actor.get(actor, ()))
