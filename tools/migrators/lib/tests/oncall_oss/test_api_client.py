from unittest.mock import MagicMock, patch

from lib.oncall.api_client import OnCallAPIClient


@patch("lib.oncall.api_client._api_call")
def test_list_all_paginates(mock_api_call):
    mock_api_call.side_effect = [
        MagicMock(json=MagicMock(return_value={"results": [{"id": "1"}], "next": "schedules/?page=2"})),
        MagicMock(json=MagicMock(return_value={"results": [{"id": "2"}], "next": None})),
    ]
    client = OnCallAPIClient("http://localhost:8080/api/v1/", "token", "oncall_oss")
    results = client.list_all("schedules")
    assert len(results) == 2
    assert results[0]["id"] == "1"
    assert results[1]["id"] == "2"
    assert mock_api_call.call_count == 2


@patch("lib.oncall.api_client._api_call")
def test_list_all_single_page(mock_api_call):
    mock_api_call.return_value = MagicMock(
        json=MagicMock(return_value={"results": [{"id": "1"}], "next": None})
    )
    client = OnCallAPIClient("http://localhost:8080/api/v1/", "token", "oncall_oss")
    results = client.list_all("schedules")
    assert len(results) == 1
    mock_api_call.assert_called_once()
