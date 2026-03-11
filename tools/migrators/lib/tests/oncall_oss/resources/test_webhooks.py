from unittest.mock import patch

from lib.oncall_oss.resources.webhooks import match_webhook, migrate_webhook


def test_match_webhook():
    webhook = {"id": "w1", "name": "My Webhook"}
    oncall_webhooks = [
        {"id": "ow1", "name": "My Webhook"},
        {"id": "ow2", "name": "Other"},
    ]
    match_webhook(webhook, oncall_webhooks)
    assert webhook["oncall_webhook"]["id"] == "ow1"


def test_match_webhook_no_match():
    webhook = {"id": "w1", "name": "Brand New"}
    oncall_webhooks = [{"id": "ow1", "name": "Other"}]
    match_webhook(webhook, oncall_webhooks)
    assert webhook["oncall_webhook"] is None


@patch("lib.oncall_oss.resources.webhooks.OnCallAPIClient")
def test_migrate_webhook_creates_new(mock_client):
    mock_client.create.return_value = {"id": "ow_new", "name": "My Webhook"}
    webhook = {
        "id": "w1",
        "name": "My Webhook",
        "url": "https://example.com/hook",
        "http_method": "POST",
        "trigger_type": "escalation",
        "forward_all": True,
        "is_webhook_enabled": True,
        "oncall_webhook": None,
        "extra_api_field": "should_be_ignored",
    }

    result = migrate_webhook(webhook)

    assert result["id"] == "ow_new"
    create_payload = mock_client.create.call_args[0][1]
    assert create_payload["name"] == "My Webhook"
    assert create_payload["url"] == "https://example.com/hook"
    assert "extra_api_field" not in create_payload
    assert "id" not in create_payload
    assert "oncall_webhook" not in create_payload
    mock_client.delete.assert_not_called()


@patch("lib.oncall_oss.resources.webhooks.OnCallAPIClient")
def test_migrate_webhook_replaces_existing(mock_client):
    mock_client.create.return_value = {"id": "ow_new", "name": "My Webhook"}
    webhook = {
        "id": "w1",
        "name": "My Webhook",
        "url": "https://example.com/hook",
        "http_method": "POST",
        "trigger_type": "escalation",
        "oncall_webhook": {"id": "ow_existing"},
    }

    result = migrate_webhook(webhook)

    assert result["id"] == "ow_new"
    mock_client.delete.assert_called_once_with("webhooks/ow_existing")
