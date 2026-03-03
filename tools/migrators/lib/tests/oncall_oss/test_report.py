from lib.oncall_oss.report import (
    format_escalation_chain,
    format_integration,
    format_schedule,
    format_user,
    integration_report,
    schedule_report,
    user_report,
)


def test_format_user():
    assert format_user({"username": "alice@example.com"}) == "alice@example.com"


def test_format_schedule():
    assert format_schedule({"name": "Primary"}) == "Primary"


def test_format_escalation_chain():
    assert format_escalation_chain({"name": "Critical"}) == "Critical"


def test_format_integration():
    assert format_integration({"name": "Webhook"}) == "Webhook"


def test_user_report():
    users = [
        {"id": "u1", "username": "a@x.com", "oncall_user": {"id": "ou1"}},
        {"id": "u2", "username": "b@x.com", "oncall_user": None},
    ]
    report = user_report(users)
    assert "✅" in report
    assert "❌" in report
    assert "a@x.com" in report
    assert "b@x.com" in report


def test_schedule_report():
    schedules = [
        {"name": "S1", "oncall_schedule": None},
        {"name": "S2", "oncall_schedule": {"id": "os2"}},
    ]
    report = schedule_report(schedules)
    assert "S1" in report
    assert "S2" in report
    assert "existing schedule will be replaced" in report


def test_integration_report():
    integrations = [
        {"name": "I1", "oncall_integration": None},
        {"name": "I2", "oncall_integration": {"id": "oi2"}},
    ]
    report = integration_report(integrations)
    assert "I1" in report
    assert "I2" in report
