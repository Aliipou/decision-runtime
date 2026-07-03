"""Production-hardening behaviours: concurrency safety, crash containment,
observability. These exercise the runtime the way real load would."""

from __future__ import annotations

import concurrent.futures as cf

from conftest import POLICY, action

from decision_runtime import RuntimeManager


def test_concurrent_submissions_are_safe(rt):
    rt.spawn("agent:bot", "bot-1")
    n = 40

    def one(i):
        return rt.submit("bot-1", action(nonce=f"n{i}"))

    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        outs = list(ex.map(one, range(n)))

    assert all(o.verdict == "ALLOW" and o.executed for o in outs)
    # No lost/dup writes, chain intact under concurrency.
    assert len(rt._dos.log.entries()) == n
    assert rt._dos.log.verify() is True
    assert rt.metrics["ALLOW"] == n


def test_crashing_tool_is_contained_and_supervised(tmp_path):
    def boom(_p):
        raise ValueError("kaboom")

    rt = RuntimeManager(POLICY, audit_path=str(tmp_path / "a.jsonl"), tools={"send_email": boom})
    s = rt.spawn("agent:bot", "bot-1")

    out = rt.submit("bot-1", action())
    # The crash did NOT propagate; it was contained and supervised.
    assert out.executed is False and out.verdict == "ERROR"
    assert "kaboom" in (out.refused_reason or "")
    assert rt.supervisor.failures(s) == 1 and rt.metrics["FAILED"] == 1
    # Within restart budget, the agent is kept alive and the runtime still works.
    assert s.can_act is True


def test_repeated_crashes_eventually_terminate_the_agent(tmp_path):
    def boom(_p):
        raise RuntimeError("down")

    rt = RuntimeManager(POLICY, audit_path=str(tmp_path / "a.jsonl"), tools={"send_email": boom})
    s = rt.spawn("agent:bot", "bot-1")
    from decision_runtime import RuntimeError_

    outcomes = 0
    for _ in range(5):
        if not s.can_act:
            break
        rt.submit("bot-1", action())
        outcomes += 1
    # After exceeding the restart budget the supervisor terminated the agent.
    assert s.state.value == "TERMINATED"
    try:
        rt.submit("bot-1", action())
        raise AssertionError("terminated agent should not be able to submit")
    except RuntimeError_:
        pass
