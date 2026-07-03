from __future__ import annotations

import pytest

from decision_runtime import RuntimeManager

POLICY = {
    "grants": {"agent:bot": ["tool:send_email"], "agent:reader": ["tool:read"]},
    "purpose_bindings": {"customer_support": ["support_reply"]},
    "redactions": [{"action_purpose": "support_reply", "redact_fields": ["ssn"]}],
    "contain_threat_classes": ["malicious"],
    "default": "deny",
}


@pytest.fixture
def calls():
    return []


@pytest.fixture
def rt(tmp_path, calls):
    def send_email(p):
        calls.append(("send_email", dict(p)))
        return "sent"

    def read(p):
        calls.append(("read", dict(p)))
        return "read-ok"

    def wire_money(p):
        calls.append(("wire_money", dict(p)))
        return "wired"

    tools = {"send_email": send_email, "read": read, "wire_money": wire_money}
    return RuntimeManager(POLICY, audit_path=str(tmp_path / "audit.jsonl"), tools=tools)


def action(**kw):
    base = {
        "actor": "agent:bot", "tool": "send_email", "capability": "tool:send_email",
        "action_purpose": "support_reply", "data_labels": ["customer_support"],
        "payload": {}, "nonce": "n-1",
    }
    base.update(kw)
    return base
