"""Resource management — quotas + limits. An AVAILABILITY control, not authority.

Refusing an action for being over-quota is a *runtime* decision about resources,
never a *security* decision about permission — the kernel still governs whether a
within-quota action is allowed. Exceeding a quota returns a runtime refusal before
the action ever reaches the kernel.

Real here: a per-agent token-bucket rate limiter. Honest limit: the execution
`timeout_seconds` is advisory metadata — a *hard* wall-clock kill needs OS-level
isolation (subprocess/container), which is out of scope for this library (see
PRODUCTION_READINESS.md).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


@dataclass
class ResourceManager:
    rate_per_sec: float = 50.0        # sustained actions/sec per agent
    burst: int = 50                    # bucket capacity
    timeout_seconds: float = 5.0       # advisory execution budget (see note above)
    _buckets: dict[str, tuple[float, float]] = field(default_factory=dict)  # agent -> (tokens, ts)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def allow(self, agent_id: str) -> bool:
        """Consume one token for this agent. False if over quota (refuse)."""
        now = time.monotonic()
        with self._lock:
            tokens, ts = self._buckets.get(agent_id, (float(self.burst), now))
            tokens = min(self.burst, tokens + (now - ts) * self.rate_per_sec)
            if tokens < 1.0:
                self._buckets[agent_id] = (tokens, now)
                return False
            self._buckets[agent_id] = (tokens - 1.0, now)
            return True
