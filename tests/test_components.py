from __future__ import annotations

import pytest

from decision_runtime import (
    FifoScheduler,
    InMemoryState,
    NoIsolation,
    SandboxIsolation,
    Scheduler,
    Session,
    State,
    Supervisor,
)


def test_scheduler_is_fifo_and_reports_empty():
    s = FifoScheduler()
    assert isinstance(s, Scheduler) and len(s) == 0 and s.dequeue() is None
    for i in range(3):
        s.enqueue(i)
    assert len(s) == 3
    assert [s.dequeue(), s.dequeue(), s.dequeue()] == [0, 1, 2]  # order preserved
    assert s.dequeue() is None


def test_state_is_per_agent_and_clearable():
    st = InMemoryState()
    st.set("a", "k", 1); st.set("b", "k", 2)
    assert st.get("a", "k") == 1 and st.get("b", "k") == 2   # isolated per agent
    assert st.get("a", "missing") is None
    st.clear("a")
    assert st.get("a", "k") is None and st.get("b", "k") == 2


def test_supervisor_restarts_within_budget_then_terminates():
    sup = Supervisor(max_restarts=2)
    s = Session("a", "agent:bot"); s.start()
    assert sup.record_failure(s) == "restart" and s.state is State.RUNNING and s.restarts == 1
    assert sup.record_failure(s) == "restart" and s.restarts == 2
    assert sup.record_failure(s) == "terminate" and s.state is State.TERMINATED
    assert sup.failures(s) == 3


def test_supervisor_restarts_a_created_session():
    sup = Supervisor()
    s = Session("a", "agent:bot")           # never started
    assert sup.record_failure(s) == "restart" and s.state is State.RUNNING


def test_no_isolation_runs_inproc_sandbox_is_honest_stub():
    assert isinstance(NoIsolation(), object)
    seen = {}
    assert NoIsolation().run(lambda p: seen.update(p) or "ok", {"x": 1}) == "ok"
    assert seen == {"x": 1}
    with pytest.raises(NotImplementedError):
        SandboxIsolation().run(lambda p: "x", {})
