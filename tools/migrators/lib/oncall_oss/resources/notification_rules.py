"""
Migrate personal notification rules from OnCall OSS to IRM.
Same API shape; we remap user_id only.
"""

from typing import Dict

from lib.oncall.api_client import OnCallAPIClient
from lib.oncall_oss.config import PRESERVE_EXISTING_USER_NOTIFICATION_RULES


def migrate_notification_rules(
    user: dict, user_id_map: Dict[str, str]
) -> None:
    """Migrate personal notification rules for one user from OSS to IRM."""
    oncall_user = user.get("oncall_user")
    if not oncall_user:
        return

    oss_user_id = user.get("id")
    if oss_user_id not in user_id_map:
        return

    target_user_id = user_id_map[oss_user_id]
    existing_rules = oncall_user.get("notification_rules") or []

    if PRESERVE_EXISTING_USER_NOTIFICATION_RULES and existing_rules:
        return

    if not PRESERVE_EXISTING_USER_NOTIFICATION_RULES and existing_rules:
        for rule in existing_rules:
            OnCallAPIClient.delete(f"personal_notification_rules/{rule['id']}")

    for rule in user.get("notification_rules") or []:
        payload = {
            "user_id": target_user_id,
            "type": rule.get("type", "notify_by_slack"),
            "important": rule.get("important", False),
        }
        if rule.get("type") == "wait" and "duration" in rule:
            payload["duration"] = rule["duration"]
        OnCallAPIClient.create("personal_notification_rules", payload)
