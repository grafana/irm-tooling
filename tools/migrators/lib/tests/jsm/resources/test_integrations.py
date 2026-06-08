from lib.jsm.resources.integrations import link_escalation_to_integration, match_integration


def test_match_integration_maps_type():
    integration = {"name": "Webhook", "type": "Webhook"}
    match_integration(integration, [])
    assert integration["oncall_type"] == "webhook"


def test_link_escalation_to_integration_by_team():
    integration = {"teamId": "t1", "name": "I1", "type": "Webhook"}
    escalations = [
        {
            "teamId": "t1",
            "oncall_escalation_chain": {"id": "chain1"},
        }
    ]
    link_escalation_to_integration(integration, escalations)
    assert integration["oncall_escalation_chain"]["id"] == "chain1"
