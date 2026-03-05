"""
Migrate integrations and routes from OnCall OSS to IRM.
Same API shape; we remap integration_id, escalation_chain_id on routes.
"""

from typing import Dict, List

from lib.oncall.api_client import OnCallAPIClient


def match_integration(integration: dict, oncall_integrations: List[dict]) -> None:
    """Match OSS integration to target integration by name (case-insensitive)."""
    oncall_integration = None
    for candidate in oncall_integrations:
        if (integration.get("name") or "").lower().strip() == (
            candidate.get("name") or ""
        ).lower().strip():
            oncall_integration = candidate
            break
    integration["oncall_integration"] = oncall_integration


def migrate_integration(
    integration: dict,
    routes: List[dict],
    chain_id_map: Dict[str, str],
) -> dict:
    """Create or replace integration and its routes in target IRM."""
    if integration.get("oncall_integration"):
        OnCallAPIClient.delete(
            f"integrations/{integration['oncall_integration']['id']}"
        )

    payload = {
        "name": integration.get("name") or "Migrated integration",
        "type": integration.get("type") or "webhook",
        "team_id": integration.get("team_id"),
    }
    if payload["team_id"] is None:
        payload["team_id"] = None

    new_integration = OnCallAPIClient.create("integrations", payload)
    integration["oncall_integration"] = new_integration
    new_integration_id = new_integration["id"]

    sorted_routes = sorted(routes, key=lambda r: r.get("position", 0))
    default_route = sorted_routes[0] if sorted_routes else None
    other_routes = sorted_routes[1:] if len(sorted_routes) > 1 else []

    target_routes = OnCallAPIClient.list_all(
        f"routes/?integration_id={new_integration_id}"
    )
    default_route_id = target_routes[0]["id"] if target_routes else None

    if default_route and default_route_id:
        old_chain_id = default_route.get("escalation_chain_id")
        if old_chain_id and old_chain_id in chain_id_map:
            OnCallAPIClient.update(
                f"routes/{default_route_id}",
                {"escalation_chain_id": chain_id_map[old_chain_id]},
            )

    for route in sorted(other_routes, key=lambda r: r.get("position", 0)):
        old_chain_id = route.get("escalation_chain_id")
        if old_chain_id not in chain_id_map:
            continue
        route_payload = {
            "integration_id": new_integration_id,
            "escalation_chain_id": chain_id_map[old_chain_id],
            "routing_type": route.get("routing_type") or "jinja2",
            "routing_regex": route.get("routing_regex") or "{{ true }}",
            "position": route.get("position", 0),
        }
        OnCallAPIClient.create("routes", route_payload)

    return new_integration
