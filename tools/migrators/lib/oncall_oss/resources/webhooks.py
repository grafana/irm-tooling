"""
Migrate outgoing webhooks from OnCall OSS to IRM.
Same API shape; we copy the webhook configuration as-is.
"""

from typing import List

from lib.oncall.api_client import OnCallAPIClient

WEBHOOK_WRITABLE_FIELDS = {
    "name",
    "team_id",
    "url",
    "data",
    "username",
    "password",
    "authorization_header",
    "trigger_template",
    "headers",
    "http_method",
    "trigger_type",
    "integration_filter",
    "is_webhook_enabled",
    "forward_all",
}


def match_webhook(webhook: dict, oncall_webhooks: List[dict]) -> None:
    """Match OSS webhook to target webhook by name (case-insensitive)."""
    oncall_webhook = None
    for candidate in oncall_webhooks:
        if (webhook.get("name") or "").lower().strip() == (
            candidate.get("name") or ""
        ).lower().strip():
            oncall_webhook = candidate
            break
    webhook["oncall_webhook"] = oncall_webhook


def migrate_webhook(webhook: dict) -> dict:
    """Create or replace outgoing webhook in target IRM."""
    if webhook.get("oncall_webhook"):
        OnCallAPIClient.delete(f"webhooks/{webhook['oncall_webhook']['id']}")

    payload = {k: v for k, v in webhook.items() if k in WEBHOOK_WRITABLE_FIELDS}

    new_webhook = OnCallAPIClient.create("webhooks", payload)
    webhook["oncall_webhook"] = new_webhook
    return new_webhook
