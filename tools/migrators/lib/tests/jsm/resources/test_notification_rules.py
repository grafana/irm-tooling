from lib.jsm.resources.notification_rules import transform_notification_rules


def test_transform_notification_rules_includes_wait_and_notify():
    steps = [
        {
            "enabled": True,
            "sendAfter": 5,
            "contact": {"method": "email", "to": "a@example.com"},
        }
    ]
    rules = transform_notification_rules(steps, "ou1", important=False)
    assert rules[0]["type"] == "wait"
    assert rules[1]["type"] == "notify_by_email"
