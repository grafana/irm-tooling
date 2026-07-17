from unittest.mock import patch

from lib.jsm.resources.escalation_chains import _normalize_escalation, filter_escalations


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


@patch("lib.jsm.resources.escalation_chains.JSM_FILTER_ESCALATION_REGEX", "^Prod")
@patch("lib.jsm.resources.escalation_chains.JSM_FILTER_TEAM", None)
def test_filter_escalations_by_regex():
    escalations = [
        {"name": "Prod Esc", "teamId": "t1"},
        {"name": "Dev Esc", "teamId": "t1"},
    ]
    filtered = filter_escalations(escalations)
    assert [e["name"] for e in filtered] == ["Prod Esc"]
