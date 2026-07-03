# Production readiness — an honest checklist

**Verdict: production-*hardened* as a library, NOT production-*ready* as a system.**

"Production-ready" for an agent runtime is defined by properties, not by lines of
code. Below is exactly what was hardened (and is tested), and exactly what remains
— because the remaining items cannot be made true by writing more code here. They
require OS-level machinery, real deployment, real load, and independent review.

## ✅ Hardened in code (tested)

| Concern | What was done | Proof |
|---|---|---|
| **Concurrency** | `AgentRegistry`, `InMemoryState`, `FifoScheduler` are lock-guarded; the runtime serializes kernel access (the core's one-time-token store isn't proven atomic) | `test_concurrent_submissions_are_safe` (40 threaded submissions, chain intact) |
| **Crash containment** | a tool that raises is caught, never propagates; the supervisor decides restart/terminate | `test_crashing_tool_is_contained_and_supervised`, `test_repeated_crashes_eventually_terminate_the_agent` |
| **Resilience budget** | bounded restarts, then terminate | supervisor tests |
| **Observability** | structured logging + per-verdict / failure metrics (`RuntimeManager.metrics`) | `test_concurrent_...` asserts metrics |
| **Authority safety** | runtime holds no key; denied actions can't execute; actor cannot be spoofed | `test_runtime_authority.py` |
| **Lifecycle correctness** | explicit state machine, illegal transitions rejected | `test_lifecycle.py` |

Also clean: `ruff`, `mypy`, 22 tests.

## ❌ NOT done — and why code alone can't close it

| Requirement | Why it's not "just code" |
|---|---|
| **Real isolation** | `NoIsolation` runs in-process (not a boundary). True isolation needs an **OS-level sandbox** — container / namespaces / seccomp / microVM — provided by the deployment, not a library. `SandboxIsolation` is an honest stub. |
| **Durability** | the audit/state are in a local file / memory; real durability (fsync, WAL, replicated state, crash-consistent recovery) is a storage-layer + core concern, and the core is deliberately frozen. |
| **HA / distribution / failover** | single-process today; a cluster is a system, built and *operated*, not typed. |
| **Load & scale validation** | no throughput/latency numbers under concurrency at scale; the single kernel lock is a known throughput ceiling. Unproven until measured on real load. |
| **Backpressure / rate limiting / quotas** | the scheduler orders but does not shed load. Needs real traffic to design correctly. |
| **Deployment hardening** | containerization, config/secrets management, TLS, network policy — belong to the ingress/platform. |
| **Independent security audit** | the strongest claim a project makes about itself is still self-assessed until an outside party attacks it. |

## What "production-ready" would actually take

1. Wire a real isolation backend (gVisor/Firecracker/container) behind `Isolation`.
2. Durable, replicated audit + state; crash-consistent recovery.
3. Remove the global kernel lock (make the core token store atomic, or shard).
4. Load/soak testing with published numbers; backpressure.
5. Deployment (image, config, secrets, TLS) + an SRE runbook.
6. An independent security audit.

Until those exist, this is a **hardened experimental library** you can build on —
not a system to run untrusted agents in production. Claiming otherwise would be the
exact overclaim this project refuses to make.
