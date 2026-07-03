# decision-runtime — experimental Agent Runtime Platform (Path B)

**Status: EXPERIMENTAL — a *working, tested* library, but NOT production-grade.**
It runs single-process, has no real isolation (stub) and no distribution. "Ready"
means *ready to build on*, not *ready to deploy at scale*.

This is the **research track (Path B)**. The product priority remains **Path A**
(`decision-os-min`: stable kernel + SDK + Plugin API + validation) — this track
only earns real investment once a real user needs a managed agent runtime.

```python
from decision_runtime import RuntimeManager

rt = RuntimeManager(policy, audit_path="audit.jsonl", tools=TOOLS)
bot = rt.spawn("agent:bot")               # register + start a session
out = rt.submit(bot.session_id, action)   # routed THROUGH the kernel; runtime never decides
```

> **Name, honestly:** this is deliberately *not* called "Decision OS". That name
> is earned only once Runtime, Scheduler, Resource Manager, Memory, IPC, and
> Lifecycle mature into genuine agent-OS features — a title should have technical
> backing, not precede it. Until then it is `decision-runtime`.

> The kernel does not need a runtime to become infrastructure. This track only
> matters after the kernel has proven it solves a real problem for real users;
> until then, building it risks years of work on an unvalidated premise.

## Scope: an Agent Runtime *Platform* (not just "running agents")

"Runtime" here is broader than executing an agent. If this track ever matures, it
is the platform that may own:

- **Session management** and **agent lifecycle** (create/suspend/resume/terminate)
- **Resource scheduling** (ordering only — never a security decision)
- **Isolation** (sandboxing agent execution)
- **Capability routing** (getting an agent's action to the kernel and its verdict back)
- **Multi-agent coordination** and **IPC** (message passing between agents)
- **State recovery** (crash → restart → resume)
- **Plugin loading** (hosting the ecosystem's plugins at runtime)

All of it under one unbreakable rule (below). None of these are built yet — they
are the *scope* of the platform, not its current contents.

## What's real vs. stubbed (honest)

**Real + tested (19 tests, ruff + mypy clean):**
- `session.py` — lifecycle state machine (CREATED→RUNNING→SUSPENDED→TERMINATED), illegal transitions rejected.
- `registry.py` — agent/identity registry.
- `scheduler.py` — FIFO ordering only; **makes no security decisions**.
- `state.py` — per-agent in-memory state (+ backend Protocol).
- `supervisor.py` — restart budget → restart/terminate.
- `runtime.py` — **RuntimeManager**: binds actor to session (anti-spoof), routes every action through the kernel, drains the scheduler, audits everything.

**Stub / interface-only (honest):**
- `isolation.py` — real isolation needs OS-level sandboxing (containers/seccomp/microVM); default is `NoIsolation` (in-process, *not* a boundary).

## The one unbreakable invariant (tested)

**The runtime holds no authority.** It owns no signing key, constructs no decision,
mints no token. Every real-effect action routes through the `decision-os-min`
kernel; the runtime decides only *when* an agent may act, never *whether an action
is allowed*. Proven by `tests/test_runtime_authority.py` — a denied action cannot
be executed via the runtime, and an agent cannot spoof another's identity.

## Not yet built (the platform's future scope)

Multi-agent coordination, IPC, real isolation, state recovery beyond restart,
plugin loading, distribution. Scope — not current contents. Resume only on a real
user's real need.
