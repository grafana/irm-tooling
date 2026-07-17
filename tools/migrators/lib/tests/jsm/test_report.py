from lib.jsm.report import escalation_report, integration_report, user_report


def _escalation(name, rules, oncall_escalation_chain=None):
    return {
        "oncall_escalation_chain": oncall_escalation_chain,
        "_normalized_policy": {
            "name": name,
            "ownerTeam": {"id": "t1", "name": "Team A"},
            "rules": rules,
        },
    }


def test_user_report_shows_match_and_no_match():
    users = [
        {"fullName": "A", "email": "a@x.com", "oncall_user": {"id": "ou1", "notification_rules": []}},
        {"fullName": "B", "email": "b@x.com", "oncall_user": None},
    ]
    report = user_report(users)
    assert "✅" in report
    assert "❌" in report


def test_integration_report_unsupported_type():
    integrations = [{"name": "X", "type": "Unknown", "oncall_integration": None, "oncall_type": None}]
    report = integration_report(integrations)
    assert "unsupported integration type" in report


def test_escalation_report_flags_skipped_non_default_notify_type():
    escalations = [
        _escalation("All non-default", [{"notifyType": "next"}]),
        _escalation("Has default", [{"notifyType": "default"}]),
    ]
    report = escalation_report(escalations)
    assert "will be skipped (all rules have a non-default notifyType)" in report
    assert "✅" in report
