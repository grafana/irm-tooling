"""
Migrate escalation chains and their policy steps from OnCall OSS to IRM.
Same API shape; we remap escalation_chain_id, user IDs, and schedule IDs.
"""

from typing import Dict, List

from lib.oncall.api_client import OnCallAPIClient


def match_escalation_chain(chain: dict, oncall_chains: List[dict]) -> None:
    """Match OSS chain to target chain by name (case-insensitive)."""
    oncall_chain = None
    for candidate in oncall_chains:
        if (chain.get("name") or "").lower().strip() == (
            candidate.get("name") or ""
        ).lower().strip():
            oncall_chain = candidate
            break
    chain["oncall_escalation_chain"] = oncall_chain


def _remap_policy_step(
    step: dict,
    new_chain_id: str,
    user_id_map: Dict[str, str],
    schedule_id_map: Dict[str, str],
) -> dict:
    """Build create payload for one escalation policy step with IDs remapped."""
    payload = {
        "escalation_chain_id": new_chain_id,
        "position": step.get("position", 0),
        "type": step["type"],
    }
    if step.get("important") is not None:
        payload["important"] = step["important"]
    if step.get("type") == "wait" and "duration" in step:
        payload["duration"] = step["duration"]
    if step.get("type") == "notify_persons":
        payload["persons_to_notify"] = [
            user_id_map[uid] for uid in (step.get("persons_to_notify") or []) if uid in user_id_map
        ]
        if not payload["persons_to_notify"]:
            return None
    if step.get("type") == "notify_person_next_each_time":
        payload["persons_to_notify_next_each_time"] = [
            user_id_map[uid]
            for uid in (step.get("persons_to_notify_next_each_time") or [])
            if uid in user_id_map
        ]
        if not payload["persons_to_notify_next_each_time"]:
            return None
    if step.get("type") == "notify_on_call_from_schedule":
        old_schedule_id = step.get("notify_on_call_from_schedule")
        if old_schedule_id not in schedule_id_map:
            return None
        payload["notify_on_call_from_schedule"] = schedule_id_map[old_schedule_id]
    if step.get("type") == "notify_if_time_from_to":
        if "notify_if_time_from" in step:
            payload["notify_if_time_from"] = step["notify_if_time_from"]
        if "notify_if_time_to" in step:
            payload["notify_if_time_to"] = step["notify_if_time_to"]
    if step.get("type") == "trigger_webhook" and step.get("action_to_trigger"):
        payload["action_to_trigger"] = step["action_to_trigger"]
    if step.get("type") == "notify_user_group" and step.get("group_to_notify"):
        payload["group_to_notify"] = step["group_to_notify"]
    if step.get("type") == "declare_incident" and step.get("severity"):
        payload["severity"] = step["severity"]
    return payload


def migrate_escalation_chain(
    chain: dict,
    policies: List[dict],
    user_id_map: Dict[str, str],
    schedule_id_map: Dict[str, str],
) -> dict:
    """Create or replace escalation chain and its steps in target IRM."""
    if chain.get("oncall_escalation_chain"):
        OnCallAPIClient.delete(
            f"escalation_chains/{chain['oncall_escalation_chain']['id']}"
        )

    chain_payload = {
        "name": chain.get("name") or "Migrated chain",
        "team_id": chain.get("team_id"),
    }
    if chain_payload["team_id"] is None:
        chain_payload["team_id"] = None

    new_chain = OnCallAPIClient.create("escalation_chains", chain_payload)
    chain["oncall_escalation_chain"] = new_chain
    new_chain_id = new_chain["id"]

    sorted_policies = sorted(policies, key=lambda p: p.get("position", 0))
    for step in sorted_policies:
        payload = _remap_policy_step(
            step, new_chain_id, user_id_map, schedule_id_map
        )
        if payload is not None:
            OnCallAPIClient.create("escalation_policies", payload)

    return new_chain
