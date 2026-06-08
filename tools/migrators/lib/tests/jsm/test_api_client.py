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
