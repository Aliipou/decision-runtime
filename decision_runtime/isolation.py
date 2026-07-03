"""Execution isolation seam.

The default is **no isolation** (runs the effect in-process, with a clear name so
callers know the boundary is absent). Real isolation — containers / namespaces /
seccomp / microVMs — is INTERFACE-ONLY here: it needs OS-level machinery and can't
be faked in a library. The runtime works without it; wiring a real backend is the
first thing a production deployment adds.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Isolation(Protocol):
    name: str

    def run(self, fn: Callable[[dict[str, Any]], Any], payload: dict[str, Any]) -> Any: ...


class NoIsolation:
    """Runs the effect in the current process. NOT a security boundary."""

    name = "none"

    def run(self, fn: Callable[[dict[str, Any]], Any], payload: dict[str, Any]) -> Any:
        return fn(payload)


class SandboxIsolation:
    """Container/seccomp-backed isolation — INTERFACE ONLY."""

    name = "sandbox"

    def run(self, fn: Callable[[dict[str, Any]], Any], payload: dict[str, Any]) -> Any:
        raise NotImplementedError(
            "Real isolation requires an OS-level sandbox (container/namespaces/"
            "seccomp/microVM). Wire it here for production."
        )
