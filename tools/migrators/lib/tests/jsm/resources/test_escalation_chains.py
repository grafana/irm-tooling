from lib.jsm.resources.escalation_chains import _normalize_escalation


def test_normalize_escalation_maps_delay_and_team():
    escalation = {
        "id": "e1",
        "name": "Esc",
        "teamId": "t1",
        "teamName": "Team A",
        "rules": [
            {
                "notifyType": "default",
                "delay": 5,
                "recipient": {"type": "user", "id": "u1"},
            }
        ],
    }
    policy = _normalize_escalation(escalation)
    assert policy["ownerTeam"]["name"] == "Team A"
    assert policy["rules"][0]["delay"] == {"timeAmount": 5}
