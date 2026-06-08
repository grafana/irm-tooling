import re
from typing import List

from lib.jsm.config import JSM_FILTER_ESCALATION_REGEX, JSM_FILTER_TEAM
from lib.opsgenie.resources.escalation_policies import (
    determine_policy_name,
    match_escalation_policy,
    match_users_and_schedules_for_escalation_policy,
    migrate_escalation_policy,
)


def filter_escalations(escalations: list[dict]) -> list[dict]:
    if JSM_FILTER_TEAM:
        escalations = [e for e in escalations if e.get("teamId") == JSM_FILTER_TEAM]

    if JSM_FILTER_ESCALATION_REGEX:
        pattern = re.compile(JSM_FILTER_ESCALATION_REGEX)
        escalations = [
            e for e in escalations if pattern.match(determine_policy_name(e))
        ]

    return escalations


def _normalize_escalation(escalation: dict) -> dict:
    """Convert JSM escalation payload to Opsgenie-compatible shape for reuse."""
    rules = []
    for rule in escalation.get("rules", []):
        delay = rule.get("delay")
        if isinstance(delay, (int, float)):
            delay_payload = {"timeAmount": int(delay)}
        else:
            delay_payload = delay

        rules.append(
            {
                "notifyType": rule.get("notifyType", "default"),
                "delay": delay_payload,
                "recipient": rule.get("recipient", {}),
            }
        )

    return {
        "id": escalation["id"],
        "name": escalation["name"],
        "ownerTeam": {
            "id": escalation.get("teamId", ""),
            "name": escalation.get("teamName", escalation.get("teamId", "")),
        },
        "rules": rules,
    }


def normalize_and_match_escalation(
    escalation: dict, oncall_escalation_chains: List[dict]
) -> dict:
    policy = _normalize_escalation(escalation)
    match_escalation_policy(policy, oncall_escalation_chains)
    escalation["oncall_escalation_chain"] = policy["oncall_escalation_chain"]
    escalation["_normalized_policy"] = policy
    return policy


def match_users_and_schedules_for_escalation(
    escalation: dict, users: List[dict], schedules: List[dict]
) -> None:
    policy = escalation.get("_normalized_policy") or _normalize_escalation(escalation)
    match_users_and_schedules_for_escalation_policy(policy, users, schedules)
    escalation["_normalized_policy"] = policy


def migrate_escalation(
    escalation: dict, users: List[dict], schedules: List[dict]
) -> None:
    policy = escalation.get("_normalized_policy") or _normalize_escalation(escalation)
    migrate_escalation_policy(policy, users, schedules)
    escalation["oncall_escalation_chain"] = policy["oncall_escalation_chain"]
