from unittest.mock import MagicMock, patch

from lib.jsm.api_client import JsmAPIClient


@patch("lib.jsm.api_client.api_call")
def test_list_all_paginates(mock_api_call):
    mock_api_call.side_effect = [
        MagicMock(
            json=lambda: {
                "values": [{"id": "1"}],
                "links": {"next": "/v1/schedules?offset=1&size=1"},
            }
        ),
        MagicMock(json=lambda: {"values": [{"id": "2"}], "links": {}}),
    ]

    client = JsmAPIClient(
        api_base_url="https://example.com/v1/",
        email="a@b.com",
        api_token="token",
    )
    result = client.list_schedules()

    assert len(result) == 2
    assert mock_api_call.call_count == 2


@patch("lib.jsm.api_client.api_call")
def test_list_users_from_resources_merges_multiple_create_alert_rules(mock_api_call):
    mock_api_call.return_value = MagicMock(json=lambda: {})

    client = JsmAPIClient(
        api_base_url="https://example.com/v1/",
        email="a@b.com",
        api_token="token",
    )
    notification_rules = [
        {
            "actionType": "create-alert",
            "steps": [
                {
                    "enabled": True,
                    "sendAfter": 0,
                    "contact": {"method": "email", "to": "a@example.com"},
                }
            ],
        },
        {
            "actionType": "create-alert",
            "steps": [
                {
                    "enabled": True,
                    "sendAfter": 5,
                    "contact": {"method": "sms", "to": "a@example.com"},
                }
            ],
        },
    ]

    users = client.list_users_from_resources([], [], notification_rules)

    assert len(users) == 1
    assert len(users[0]["notification_rules"]) == 2
