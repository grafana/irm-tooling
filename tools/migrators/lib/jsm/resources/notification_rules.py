from lib.jsm.config import (
    JSM_TO_ONCALL_CONTACT_METHOD_MAP,
    PRESERVE_EXISTING_USER_NOTIFICATION_RULES,
)
from lib.oncall.api_client import OnCallAPIClient
from lib.utils import transform_wait_delay


def migrate_notification_rules(user: dict) -> None:
    if (
        PRESERVE_EXISTING_USER_NOTIFICATION_RULES
        and user["oncall_user"]["notification_rules"]
    ):
        return

    if (
        not PRESERVE_EXISTING_USER_NOTIFICATION_RULES
        and user["oncall_user"]["notification_rules"]
    ):
        for rule in user["oncall_user"]["notification_rules"]:
            OnCallAPIClient.delete(f"personal_notification_rules/{rule['id']}")

    for important in (False, True):
        oncall_rules = transform_notification_rules(
            user["notification_rules"], user["oncall_user"]["id"], important
        )
        for rule in oncall_rules:
            OnCallAPIClient.create("personal_notification_rules", rule)


def transform_notification_rules(
    notification_steps: list[dict], user_id: str, important: bool
) -> list[dict]:
    sorted_steps = sorted(
        notification_steps,
        key=lambda step: step.get("sendAfter", 0),
    )

    oncall_rules = []

    for step in sorted_steps:
        if not step.get("enabled", True):
            continue

        time_amount = step.get("sendAfter", 0)
        if isinstance(time_amount, dict):
            time_amount = time_amount.get("timeAmount", 0)

        if time_amount > 0:
            oncall_rules.append(
                {
                    "user_id": user_id,
                    "type": "wait",
                    "duration": transform_wait_delay(time_amount),
                    "important": important,
                }
            )

        contact_method = step.get("contact", {}).get("method")
        if contact_method == "mobile" and important:
            oncall_type = "notify_by_mobile_app_critical"
        else:
            oncall_type = JSM_TO_ONCALL_CONTACT_METHOD_MAP.get(contact_method)

        if not oncall_type:
            continue

        oncall_rules.append(
            {"user_id": user_id, "type": oncall_type, "important": important}
        )

    return oncall_rules
