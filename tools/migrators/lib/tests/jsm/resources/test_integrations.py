from unittest.mock import MagicMock, patch

from lib.jsm.resources.integrations import (
    link_escalation_to_integration,
    match_integration,
    migrate_integration,
)


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


@patch("lib.jsm.resources.integrations.OnCallAPIClient")
def test_migrate_integration_links_escalation_via_default_route(mock_oncall):
    integration = {
        "name": "Webhook",
        "type": "Webhook",
        "oncall_type": "webhook",
        "teamId": "t1",
    }
    escalations = [
        {
            "teamId": "t1",
            "oncall_escalation_chain": {"id": "chain1"},
        }
    ]
    mock_oncall.create.return_value = {"id": "int1"}
    mock_oncall.list_all.return_value = [{"id": "route1"}]

    migrate_integration(integration, escalations)

    mock_oncall.create.assert_called_once_with(
        "integrations",
        {"name": "Webhook", "type": "webhook", "team_id": None},
    )
    mock_oncall.list_all.assert_called_once_with("routes/?integration_id=int1")
    mock_oncall.update.assert_called_once_with(
        "routes/route1",
        {"escalation_chain_id": "chain1"},
    )
