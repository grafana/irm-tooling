import re
from typing import List

from lib.jsm.config import (
    JSM_FILTER_INTEGRATION_REGEX,
    JSM_FILTER_TEAM,
    JSM_TO_ONCALL_VENDOR_MAP,
    UNSUPPORTED_INTEGRATION_TO_WEBHOOKS,
)
from lib.oncall.api_client import OnCallAPIClient


def filter_integrations(integrations: list[dict]) -> list[dict]:
    if JSM_FILTER_TEAM:
        integrations = [i for i in integrations if i.get("teamId") == JSM_FILTER_TEAM]

    if JSM_FILTER_INTEGRATION_REGEX:
        pattern = re.compile(JSM_FILTER_INTEGRATION_REGEX)
        integrations = [i for i in integrations if pattern.match(i.get("name", ""))]

    return integrations


def match_integration(integration: dict, oncall_integrations: List[dict]) -> None:
    oncall_integration = None
    for candidate in oncall_integrations:
        if integration["name"].lower().strip() == candidate["name"].lower().strip():
            oncall_integration = candidate

    integration["oncall_integration"] = oncall_integration

    integration_type = JSM_TO_ONCALL_VENDOR_MAP.get(integration.get("type", ""))
    if not integration_type and UNSUPPORTED_INTEGRATION_TO_WEBHOOKS:
        integration_type = "webhook"
    integration["oncall_type"] = integration_type


def link_escalation_to_integration(
    integration: dict, escalations: List[dict]
) -> None:
    """Link integration to migrated escalation chain from same team when possible."""
    team_id = integration.get("teamId")
    if not team_id:
        return

    for escalation in escalations:
        if (
            escalation.get("teamId") == team_id
            and escalation.get("oncall_escalation_chain")
        ):
            integration["oncall_escalation_chain"] = escalation[
                "oncall_escalation_chain"
            ]
            break


def migrate_integration(integration: dict) -> None:
    if integration.get("oncall_integration"):
        OnCallAPIClient.delete(
            f"integrations/{integration['oncall_integration']['id']}"
        )

    payload = {
        "name": integration["name"],
        "type": integration["oncall_type"],
        "team_id": None,
    }

    if integration.get("oncall_escalation_chain"):
        payload["escalation_chain_id"] = integration["oncall_escalation_chain"]["id"]

    integration["oncall_integration"] = OnCallAPIClient.create("integrations", payload)
