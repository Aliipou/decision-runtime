"""Plugin loader — hosts ADVISOR plugins. They can only advise, never decide.

A loaded plugin is a `(action) -> threat_class | None` callable. The loader
composes several into one advisor that returns the **most restrictive** suggestion
(any 'malicious' wins over 'suspicious' wins over None). Composition can only
tighten — the loader cannot let a plugin author a verdict or loosen a DENY,
because its output is still just advice the kernel consults.

A misbehaving plugin (one that raises) is contained: its failure is ignored and
the remaining advisors are still consulted — a broken plugin cannot crash the
decision path, nor can it force a permit.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

log = logging.getLogger("decision-runtime")

Advisor = Callable[[dict[str, Any]], "str | None"]

# Restriction order — higher = more restrictive. Unknown classes are treated as
# the mildest advisory ("unknown") so a plugin cannot invent a stronger signal by
# returning gibberish; only the known escalations count.
_ORDER = {None: 0, "benign": 0, "unknown": 1, "suspicious": 2, "malicious": 3}


class PluginLoader:
    def __init__(self) -> None:
        self._advisors: list[tuple[str, Advisor]] = []

    def register(self, name: str, advisor: Advisor) -> None:
        self._advisors.append((name, advisor))

    def __len__(self) -> int:
        return len(self._advisors)

    def composed_advisor(self) -> Advisor:
        """Return one advisor = the most restrictive of all loaded plugins."""

        def advise(action: dict[str, Any]) -> str | None:
            worst: str | None = None
            for name, adv in self._advisors:
                try:
                    suggestion = adv(action)
                except Exception as e:  # a broken plugin cannot break the decision
                    log.warning("advisor plugin %r raised: %s (ignored)", name, e)
                    continue
                if _ORDER.get(suggestion, 1) > _ORDER.get(worst, 0):
                    worst = suggestion
            return worst

        return advise
