from unittest.mock import patch

from lib.oncall_oss.resources.integrations import (
    match_integration,
    migrate_integration,
)


def test_match_integration():
    integration = {"id": "i1", "name": "Webhook"}
    oncall_integrations = [
        {"id": "oi1", "name": "Webhook"},
        {"id": "oi2", "name": "Other"},
    ]
    match_integration(integration, oncall_integrations)
    assert integration["oncall_integration"]["id"] == "oi1"


def test_match_integration_no_match():
    integration = {"id": "i1", "name": "New Integration"}
    oncall_integrations = [{"id": "oi1", "name": "Other"}]
    match_integration(integration, oncall_integrations)
    assert integration["oncall_integration"] is None


@patch("lib.oncall_oss.resources.integrations.OnCallAPIClient")
def test_migrate_integration(mock_client):
    mock_client.create.return_value = {"id": "oi_new"}
    mock_client.list_all.return_value = [{"id": "route_default"}]
    integration = {
        "id": "i1",
        "name": "Test Integration",
        "type": "webhook",
        "oncall_integration": None,
    }
    routes = [
        {"position": 0, "escalation_chain_id": "c1"},
        {"position": 1, "escalation_chain_id": "c2", "routing_regex": ".*critical.*"},
    ]
    chain_id_map = {"c1": "oc1", "c2": "oc2"}

    result = migrate_integration(integration, routes, chain_id_map)

    assert result["id"] == "oi_new"
    mock_client.update.assert_called_once_with(
        "routes/route_default",
        {"escalation_chain_id": "oc1"},
    )
    mock_client.create.assert_any_call(
        "routes",
        {
            "integration_id": "oi_new",
            "escalation_chain_id": "oc2",
            "routing_type": "regex",
            "routing_regex": ".*critical.*",
            "position": 1,
        },
    )
