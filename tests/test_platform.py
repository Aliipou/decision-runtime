"""The platform components (memory / IPC / capability router / plugin loader /
resource manager) — real behaviour, and the invariant that NONE of them can grant
authority or bypass the kernel."""

from __future__ import annotations

from conftest import POLICY, action

from decision_runtime import (
    CapabilityRouter,
    ContextMemory,
    MessageBus,
    PluginLoader,
    ResourceManager,
    RuntimeManager,
)


# --- standalone components --------------------------------------------------
def test_memory_is_per_agent_and_bounded():
    m = ContextMemory(max_items=3)
    for i in range(5):
        m.append("a", i)
    assert m.recent("a", 10) == [2, 3, 4]        # bounded, per-agent
    assert m.recent("b") == []


def test_ipc_delivers_and_drains():
    bus = MessageBus()
    bus.send("a", "b", "hi")
    bus.send("a", "b", "again")
    assert bus.pending("b") == 2
    msgs = bus.receive("b")
    assert [m.body for m in msgs] == ["hi", "again"] and bus.pending("b") == 0


def test_capability_router_only_records_never_grants():
    cr = CapabilityRouter()
    cr.record("agent:bot", "tool:send_email", "n1")
    assert cr.count("agent:bot") == 1
    # It exposes no method to grant/authorize — it is a read-mostly ledger.
    assert not any(hasattr(cr, m) for m in ("grant", "authorize", "allow", "sign", "mint"))


def test_plugin_loader_composes_to_most_restrictive_and_contains_crashes():
    pl = PluginLoader()
    pl.register("benign", lambda a: None)
    pl.register("crasher", lambda a: (_ for _ in ()).throw(RuntimeError("boom")))
    pl.register("flagger", lambda a: "suspicious")
    advise = pl.composed_advisor()
    assert advise({}) == "suspicious"            # crasher ignored, most-restrictive wins


def test_resource_manager_rate_limits():
    rm = ResourceManager(rate_per_sec=0.0, burst=2)  # no refill -> only `burst` allowed
    assert rm.allow("a") and rm.allow("a")           # 2 tokens
    assert rm.allow("a") is False                    # exhausted


# --- integrated: components change availability/observability, NEVER authority
def _rt(tmp_path, **kw):
    tools = {"send_email": lambda p: "sent", "wire_money": lambda p: "wired"}
    return RuntimeManager(POLICY, audit_path=str(tmp_path / "a.jsonl"), tools=tools, **kw)


def test_resource_quota_refuses_without_reaching_kernel(tmp_path):
    rt = _rt(tmp_path, resources=ResourceManager(rate_per_sec=0.0, burst=1))
    rt.spawn("agent:bot", "b1")
    assert rt.submit("b1", action(nonce="1")).executed is True
    out = rt.submit("b1", action(nonce="2"))          # over quota
    assert out.verdict == "REFUSED" and out.executed is False
    # refused by RESOURCE, before the kernel -> not audited as a decision
    assert len(rt._dos.log.entries()) == 1


def test_advisor_plugin_can_only_tighten_never_permit(tmp_path):
    pl = PluginLoader()
    pl.register("evil", lambda a: "ALLOW")           # tries to force a permit
    rt = _rt(tmp_path, plugins=pl)
    rt.spawn("agent:bot", "b1")
    # 'ALLOW' is not a known threat class -> treated as mildest; a would-be DENY
    # (no capability) stays DENY. A plugin cannot manufacture a permit.
    out = rt.submit("b1", action(capability="tool:wire_money", tool="wire_money"))
    assert out.verdict == "DENY" and out.executed is False


def test_malicious_advisor_tightens_allow_to_contain(tmp_path):
    pl = PluginLoader()
    pl.register("threat", lambda a: "malicious")
    rt = _rt(tmp_path, plugins=pl)
    rt.spawn("agent:bot", "b1")
    out = rt.submit("b1", action())                  # would ALLOW, but advisor flags it
    assert out.verdict == "CONTAIN" and out.executed is False


def test_memory_and_capabilities_record_but_hold_no_authority(tmp_path):
    m, cr = ContextMemory(), CapabilityRouter()
    rt = _rt(tmp_path, memory=m, capabilities=cr)
    rt.spawn("agent:bot", "b1")
    rt.submit("b1", action(nonce="x"))
    assert m.recent("b1")[-1]["verdict"] == "ALLOW"
    assert cr.count("agent:bot") == 1                # recorded the kernel's grant
    # a denied action records no grant
    rt.submit("b1", action(nonce="y", capability="tool:wire_money", tool="wire_money"))
    assert cr.count("agent:bot") == 1
