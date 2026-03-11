from unittest.mock import patch

from lib.oncall_oss.resources.schedules import (
    _remap_shift,
    match_schedule,
    migrate_schedule,
)


def test_match_schedule():
    schedule = {"id": "s1", "name": "Primary"}
    oncall_schedules = [
        {"id": "os1", "name": "Primary"},
        {"id": "os2", "name": "Secondary"},
    ]
    match_schedule(schedule, oncall_schedules)
    assert schedule["oncall_schedule"]["id"] == "os1"


def test_match_schedule_no_match():
    schedule = {"id": "s1", "name": "New Schedule"}
    oncall_schedules = [{"id": "os1", "name": "Other"}]
    match_schedule(schedule, oncall_schedules)
    assert schedule["oncall_schedule"] is None


def test_remap_shift_rolling_users():
    shift = {
        "id": "sh1",
        "schedule_id": "s1",
        "type": "rolling_users",
        "rolling_users": [["u1"], ["u2"]],
    }
    payload = _remap_shift(shift, {"u1": "ou1", "u2": "ou2"})
    assert payload is not None
    assert "id" not in payload
    assert "schedule_id" not in payload
    assert payload["rolling_users"] == [["ou1"], ["ou2"]]


def test_remap_shift_partial_rolling_users_keeps_mapped_slots():
    """Shift with mixed mapped/unmapped slots should keep the mapped ones."""
    shift = {
        "id": "sh1",
        "schedule_id": "s1",
        "type": "rolling_users",
        "rolling_users": [["u1"], ["u2"]],
        "name": "[L1] Rotation",
        "duration": 86400,
    }
    payload = _remap_shift(shift, {"u1": "ou1"})
    assert payload is not None
    assert payload["rolling_users"] == [["ou1"]]


def test_remap_shift_override_users():
    shift = {"id": "sh1", "type": "override", "users": ["u1"]}
    payload = _remap_shift(shift, {"u1": "ou1"})
    assert payload["users"] == ["ou1"]


def test_remap_shift_unmapped_user_returns_none():
    shift = {"type": "override", "users": ["u1"]}
    payload = _remap_shift(shift, {})
    assert payload is None


def test_remap_shift_strips_readonly_fields():
    shift = {
        "id": "sh1",
        "schedule_id": "s1",
        "type": "rolling_users",
        "rolling_users": [["u1"]],
        "name": "Test",
        "duration": 86400,
        "start": "2024-01-01T00:00:00",
        "updated_shift_at": "2024-06-01",
        "some_unknown_field": "value",
    }
    payload = _remap_shift(shift, {"u1": "ou1"})
    assert "id" not in payload
    assert "schedule_id" not in payload
    assert "updated_shift_at" not in payload
    assert "some_unknown_field" not in payload
    assert payload["name"] == "Test"
    assert payload["duration"] == 86400


@patch("lib.oncall_oss.resources.schedules.OnCallAPIClient")
def test_migrate_schedule(mock_client):
    mock_client.create.side_effect = [
        {"id": "sh1"},
        {"id": "sched1", "name": "Primary"},
    ]
    schedule = {"id": "s1", "name": "Primary", "type": "web", "time_zone": "UTC", "oncall_schedule": None}
    shifts = [
        {"type": "rolling_users", "rolling_users": [["u1"]], "start": "2024-01-01T00:00:00", "duration": 86400},
    ]
    user_id_map = {"u1": "ou1"}

    result = migrate_schedule(schedule, shifts, user_id_map)

    assert result["id"] == "sched1"
    mock_client.create.assert_any_call("schedules", {"name": "Primary", "type": "web", "time_zone": "UTC", "team_id": None, "shifts": ["sh1"]})
