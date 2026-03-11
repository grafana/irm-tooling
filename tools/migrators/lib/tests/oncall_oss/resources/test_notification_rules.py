"""Tests for OnCall OSS personal notification rules migration."""

from unittest.mock import patch

from lib.oncall_oss.resources.notification_rules import migrate_notification_rules


@patch("lib.oncall_oss.resources.notification_rules.OnCallAPIClient")
@patch("lib.oncall_oss.resources.notification_rules.PRESERVE_EXISTING_USER_NOTIFICATION_RULES", True)
def test_migrate_notification_rules_preserve_skips_when_user_has_existing_rules(mock_client):
    """When preserve is True and target user already has rules, do nothing."""
    user = {
        "id": "oss_u1",
        "oncall_user": {"id": "irm_u1", "notification_rules": [{"id": "r1"}]},
        "notification_rules": [{"type": "notify_by_slack", "important": False}],
    }
    user_id_map = {"oss_u1": "irm_u1"}
    migrate_notification_rules(user, user_id_map)
    mock_client.delete.assert_not_called()
    mock_client.create.assert_not_called()


@patch("lib.oncall_oss.resources.notification_rules.OnCallAPIClient")
@patch("lib.oncall_oss.resources.notification_rules.PRESERVE_EXISTING_USER_NOTIFICATION_RULES", False)
def test_migrate_notification_rules_replace_deletes_existing_then_creates(mock_client):
    """When preserve is False and user has existing rules, delete them then create OSS rules."""
    user = {
        "id": "oss_u1",
        "oncall_user": {"id": "irm_u1", "notification_rules": [{"id": "r1"}, {"id": "r2"}]},
        "notification_rules": [
            {"type": "wait", "duration": 60},
            {"type": "notify_by_slack", "important": True},
        ],
    }
    user_id_map = {"oss_u1": "irm_u1"}
    migrate_notification_rules(user, user_id_map)
    assert mock_client.delete.call_count == 2
    mock_client.delete.assert_any_call("personal_notification_rules/r1")
    mock_client.delete.assert_any_call("personal_notification_rules/r2")
    assert mock_client.create.call_count == 2
    # create(path, payload) -> payload is second positional arg
    payloads = [c[0][1] for c in mock_client.create.call_args_list]
    assert payloads[0]["user_id"] == "irm_u1"
    assert payloads[0]["type"] == "wait"
    assert payloads[0]["duration"] == 60
    assert payloads[1]["user_id"] == "irm_u1"
    assert payloads[1]["type"] == "notify_by_slack"
    assert payloads[1]["important"] is True


@patch("lib.oncall_oss.resources.notification_rules.OnCallAPIClient")
def test_migrate_notification_rules_creates_wait_with_duration(mock_client):
    """Wait rules include duration in payload."""
    user = {
        "id": "oss_u1",
        "oncall_user": {"id": "irm_u1", "notification_rules": []},
        "notification_rules": [{"type": "wait", "duration": 300, "important": False}],
    }
    user_id_map = {"oss_u1": "irm_u1"}
    migrate_notification_rules(user, user_id_map)
    mock_client.create.assert_called_once()
    payload = mock_client.create.call_args[0][1]
    assert payload["type"] == "wait"
    assert payload["duration"] == 300
    assert payload["user_id"] == "irm_u1"


@patch("lib.oncall_oss.resources.notification_rules.OnCallAPIClient")
def test_migrate_notification_rules_no_oncall_user_returns_early(mock_client):
    """If user has no matched oncall_user, do nothing."""
    user = {"id": "oss_u1", "notification_rules": [{"type": "notify_by_slack"}]}
    user_id_map = {"oss_u1": "irm_u1"}
    migrate_notification_rules(user, user_id_map)
    mock_client.create.assert_not_called()


@patch("lib.oncall_oss.resources.notification_rules.OnCallAPIClient")
def test_migrate_notification_rules_user_not_in_map_returns_early(mock_client):
    """If OSS user id is not in user_id_map, do nothing."""
    user = {
        "id": "oss_u1",
        "oncall_user": {"id": "irm_u1", "notification_rules": []},
        "notification_rules": [{"type": "notify_by_slack"}],
    }
    user_id_map = {}
    migrate_notification_rules(user, user_id_map)
    mock_client.create.assert_not_called()
