from lib.jsm.report import integration_report, user_report


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
