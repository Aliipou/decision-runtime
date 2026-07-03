from __future__ import annotations

import pytest

from decision_runtime import AgentRegistry, LifecycleError, RegistryError, Session, State


def test_full_legal_lifecycle():
    s = Session("a", "agent:bot")
    assert s.state is State.CREATED and not s.can_act
    s.start(); assert s.state is State.RUNNING and s.can_act
    s.suspend(); assert s.state is State.SUSPENDED and not s.can_act
    s.resume(); assert s.state is State.RUNNING
    s.terminate(); assert s.state is State.TERMINATED and not s.can_act
    assert s.history == ["CREATED->RUNNING", "RUNNING->SUSPENDED",
                         "SUSPENDED->RUNNING", "RUNNING->TERMINATED"]


@pytest.mark.parametrize("bad", [
    ("suspend",),   # from CREATED
    ("resume",),    # from CREATED
])
def test_illegal_transitions_from_created_raise(bad):
    s = Session("a", "agent:bot")
    with pytest.raises(LifecycleError):
        getattr(s, bad[0])()


def test_terminated_is_final():
    s = Session("a", "agent:bot"); s.start(); s.terminate()
    for op in ("start", "suspend", "resume", "terminate"):
        with pytest.raises(LifecycleError):
            getattr(s, op)()


def test_cannot_resume_a_running_session():
    s = Session("a", "agent:bot"); s.start()
    with pytest.raises(LifecycleError):
        s.resume()


def test_registry_register_lookup_and_duplicates():
    r = AgentRegistry()
    s = r.register("agent:bot", "bot-1")
    assert r.get("bot-1") is s and len(r) == 1
    with pytest.raises(RegistryError):
        r.register("agent:bot", "bot-1")       # duplicate id
    with pytest.raises(RegistryError):
        r.get("nope")                          # unknown
    assert r.active() == []                     # not started yet
    s.start()
    assert r.active() == [s]
