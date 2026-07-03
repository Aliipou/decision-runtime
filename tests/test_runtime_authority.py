"""The security-critical contract of the runtime: it holds NO authority and
cannot be used to bypass the kernel. These are the tests that matter most."""

from __future__ import annotations

import pytest
from conftest import action

from decision_runtime import RuntimeError_


def test_runtime_owns_no_signing_key():
    # Structural: the manager must not hold a private key. The ONLY signer is the
    # kernel, reachable via the composed decision-os-min instance.
    import tempfile

    from conftest import POLICY

    from decision_runtime import RuntimeManager

    rt = RuntimeManager(POLICY, audit_path=tempfile.mktemp(), tools={})
    assert not hasattr(rt, "_key")
    # the public key is the KERNEL's, not the runtime's
    assert len(rt.kernel_public_key) == 64


def test_allow_routes_through_kernel_and_executes(rt, calls):
    rt.spawn("agent:bot", "bot-1")
    out = rt.submit("bot-1", action())
    assert out.verdict == "ALLOW" and out.executed and out.output == "sent"
    assert calls == [("send_email", {})]
    assert rt._dos.log.verify() is True                      # audited + intact


def test_runtime_cannot_execute_a_denied_action(rt, calls):
    rt.spawn("agent:bot", "bot-1")
    out = rt.submit("bot-1", action(capability="tool:wire_money", tool="wire_money"))
    assert out.verdict == "DENY" and out.executed is False
    assert calls == []                                       # nothing ran


def test_actor_cannot_be_spoofed_binds_to_session(rt, calls):
    # agent:reader (only holds tool:read) tries to act AS agent:bot on send_email.
    rt.spawn("agent:reader", "reader-1")
    out = rt.submit("reader-1", action(actor="agent:bot", capability="tool:send_email"))
    # actor is rebound to the session identity (agent:reader), which lacks the
    # capability -> DENY. The spoof buys nothing.
    assert out.verdict == "DENY" and out.executed is False
    assert calls == []


def test_suspended_and_terminated_agents_cannot_submit(rt):
    s = rt.spawn("agent:bot", "bot-1")
    s.suspend()
    with pytest.raises(RuntimeError_):
        rt.submit("bot-1", action())
    s.resume(); s.terminate()
    with pytest.raises(RuntimeError_):
        rt.submit("bot-1", action())


def test_limit_redaction_holds_through_the_runtime(rt, calls):
    rt.spawn("agent:bot", "bot-1")
    out = rt.submit("bot-1", action(payload={"ssn": "123-45-6789", "body": "hi"}))
    assert out.verdict == "LIMIT" and out.executed
    assert calls[0][1]["ssn"] == "[REDACTED]"               # tool never saw the secret


def test_scheduler_drains_in_order_and_still_gates_each(rt, calls):
    rt.spawn("agent:bot", "bot-1")
    rt.enqueue("bot-1", action(nonce="a"))                                   # ALLOW
    rt.enqueue("bot-1", action(nonce="b", capability="tool:wire_money", tool="wire_money"))  # DENY
    rt.enqueue("bot-1", action(nonce="c"))                                   # ALLOW
    outs = rt.run_pending()
    assert [o.verdict for o in outs] == ["ALLOW", "DENY", "ALLOW"]
    assert [o.executed for o in outs] == [True, False, True]
    assert [c[0] for c in calls] == ["send_email", "send_email"]             # denied one didn't run
    assert rt._dos.log.verify() is True


def test_every_submission_is_audited(rt):
    rt.spawn("agent:bot", "bot-1")
    for n in ("a", "b", "c"):
        rt.submit("bot-1", action(nonce=n))
    entries = rt._dos.log.entries()
    assert len(entries) == 3 and rt._dos.log.verify() is True
