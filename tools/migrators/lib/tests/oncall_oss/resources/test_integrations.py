from unittest.mock import patch

from lib.oncall_oss.resources.integrations import (
    is_system_managed_integration,
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


def test_match_integration_direct_paging_no_target():
    integration = {"id": "i1", "name": "Direct paging (A Team team)", "type": "direct_paging"}

    match_integration(integration, [])

    assert is_system_managed_integration(integration) is True
    assert integration["oncall_integration"] is None
    assert integration["migration_errors"]
    assert "auto-created per team" in integration["migration_errors"][0]


def test_match_integration_direct_paging_matched():
    integration = {"id": "i1", "name": "Direct paging (A Team team)", "type": "direct_paging"}
    target = [{"id": "oi1", "name": "Direct paging (A Team team)", "type": "direct_paging"}]

    match_integration(integration, target)

    assert integration["oncall_integration"]["id"] == "oi1"
    assert integration["migration_errors"] == []


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
            "routing_type": "jinja2",
            "routing_regex": ".*critical.*",
            "position": 1,
        },
    )


@patch("lib.oncall_oss.resources.integrations.OnCallAPIClient")
def test_migrate_direct_paging_updates_routes_on_existing(mock_client):
    mock_client.list_all.return_value = [{"id": "route_default"}]
    integration = {
        "id": "i1",
        "name": "Direct paging (A Team team)",
        "type": "direct_paging",
        "oncall_integration": {"id": "oi_existing"},
        "migration_errors": [],
    }
    routes = [
        {"position": 0, "escalation_chain_id": "c1"},
    ]
    chain_id_map = {"c1": "oc1"}

    result = migrate_integration(integration, routes, chain_id_map)

    assert result["id"] == "oi_existing"
    mock_client.create.assert_not_called()
    mock_client.delete.assert_not_called()
    mock_client.update.assert_called_once_with(
        "routes/route_default",
        {"escalation_chain_id": "oc1"},
    )
