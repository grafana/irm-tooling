import pytest
from unittest.mock import patch

from lib.opsgenie.resources.schedules import (
    Rotation,
    Schedule,
    TimeRestriction,
    calc_restriction_duration_seconds,
    expand_day_range,
    match_schedule,
    match_users_for_schedule,
    migrate_schedule,
)


def test_match_schedule():
    schedule = {
        "id": "s1",
        "name": "Primary Schedule",
        "timezone": "UTC",
        "rotations": [],
    }
    oncall_schedules = [
        {"id": "os1", "name": "Primary Schedule"},
        {"id": "os2", "name": "Secondary Schedule"},
    ]
    user_id_map = {}

    match_schedule(schedule, oncall_schedules, user_id_map)
    assert schedule["oncall_schedule"]["id"] == "os1"
    assert not schedule["migration_errors"]


def test_match_schedule_case_insensitive():
    schedule = {
        "id": "s1",
        "name": "Primary Schedule",
        "timezone": "UTC",
        "rotations": [],
    }
    oncall_schedules = [
        {"id": "os1", "name": "primary SCHEDULE"},
        {"id": "os2", "name": "Secondary Schedule"},
    ]
    user_id_map = {}

    match_schedule(schedule, oncall_schedules, user_id_map)
    assert schedule["oncall_schedule"]["id"] == "os1"
    assert not schedule["migration_errors"]


def test_match_schedule_with_time_restriction():
    """Time-restricted schedules should no longer be rejected."""
    schedule = {
        "id": "s1",
        "name": "Restricted Schedule",
        "timezone": "UTC",
        "rotations": [
            {
                "name": "Business Hours",
                "type": "weekly",
                "length": 1,
                "participants": [{"type": "user", "id": "u1"}],
                "startDate": "2024-01-01T00:00:00Z",
                "enabled": True,
                "timeRestriction": {
                    "type": "weekday-and-time-of-day",
                    "restrictions": [
                        {
                            "startDay": "monday",
                            "endDay": "friday",
                            "startHour": 8,
                            "startMin": 0,
                            "endHour": 17,
                            "endMin": 0,
                        }
                    ],
                },
            }
        ],
    }
    oncall_schedules = []
    user_id_map = {"u1": "ou1"}

    match_schedule(schedule, oncall_schedules, user_id_map)
    assert not schedule["migration_errors"]


def test_match_users_for_schedule():
    schedule = {
        "id": "s1",
        "name": "Primary Schedule",
        "rotations": [
            {
                "participants": [
                    {"type": "user", "id": "u1"},
                    {"type": "user", "id": "u2"},
                ],
            }
        ],
    }
    users = [
        {"id": "u1", "oncall_user": {"id": "ou1"}},
        {"id": "u2", "oncall_user": None},
        {"id": "u3", "oncall_user": {"id": "ou3"}},
    ]

    match_users_for_schedule(schedule, users)
    assert len(schedule["matched_users"]) == 1
    assert schedule["matched_users"][0]["id"] == "u1"


# ------------------------------------------------------------------
# expand_day_range / calc_restriction_duration_seconds
# ------------------------------------------------------------------


def test_expand_day_range_weekdays():
    assert expand_day_range("monday", "friday") == ["MO", "TU", "WE", "TH", "FR"]


def test_expand_day_range_full_week():
    assert expand_day_range("monday", "sunday") == [
        "MO", "TU", "WE", "TH", "FR", "SA", "SU"
    ]


def test_expand_day_range_wrap_around():
    assert expand_day_range("friday", "monday") == ["FR", "SA", "SU", "MO"]


def test_expand_day_range_single_day():
    assert expand_day_range("wednesday", "wednesday") == ["WE"]


def test_expand_day_range_invalid_start_day():
    with pytest.raises(ValueError, match="Unknown start day 'Funday'"):
        expand_day_range("Funday", "friday")


def test_expand_day_range_invalid_end_day():
    with pytest.raises(ValueError, match="Unknown end day 'Caturday'"):
        expand_day_range("monday", "Caturday")


def test_calc_restriction_duration_normal():
    assert calc_restriction_duration_seconds(
        {"startHour": 8, "startMin": 0, "endHour": 17, "endMin": 0}
    ) == 9 * 3600


def test_calc_restriction_duration_with_minutes():
    assert calc_restriction_duration_seconds(
        {"startHour": 8, "startMin": 30, "endHour": 17, "endMin": 15}
    ) == (8 * 60 + 45) * 60


def test_calc_restriction_duration_overnight():
    assert calc_restriction_duration_seconds(
        {"startHour": 22, "startMin": 0, "endHour": 6, "endMin": 0}
    ) == 8 * 3600


# ------------------------------------------------------------------
# TimeRestriction
# ------------------------------------------------------------------


def test_time_restriction_from_dict_time_of_day():
    tr = TimeRestriction.from_dict(
        {
            "type": "time-of-day",
            "restriction": {"startHour": 8, "startMin": 0, "endHour": 17, "endMin": 0},
        }
    )
    assert tr.type == "time-of-day"
    assert len(tr.restrictions) == 1
    assert tr.restrictions[0]["startHour"] == 8


def test_time_restriction_from_dict_weekday():
    tr = TimeRestriction.from_dict(
        {
            "type": "weekday-and-time-of-day",
            "restrictions": [
                {
                    "startDay": "monday",
                    "endDay": "friday",
                    "startHour": 8,
                    "startMin": 0,
                    "endHour": 17,
                    "endMin": 0,
                },
                {
                    "startDay": "saturday",
                    "endDay": "saturday",
                    "startHour": 10,
                    "startMin": 0,
                    "endHour": 14,
                    "endMin": 0,
                },
            ],
        }
    )
    assert tr.type == "weekday-and-time-of-day"
    assert len(tr.restrictions) == 2


def test_time_restriction_from_dict_unsupported_type():
    with pytest.raises(ValueError, match="Unsupported time restriction type 'custom'"):
        TimeRestriction.from_dict({"type": "custom", "restriction": {}})


def test_time_restriction_from_dict_missing_type():
    with pytest.raises(ValueError, match="Unsupported time restriction type"):
        TimeRestriction.from_dict({"restriction": {}})


# ------------------------------------------------------------------
# match_schedule — graceful error handling
# ------------------------------------------------------------------


def test_match_schedule_malformed_restriction_becomes_migration_error():
    """A malformed timeRestriction should produce a migration error, not crash."""
    schedule = {
        "id": "s1",
        "name": "Bad Schedule",
        "timezone": "UTC",
        "rotations": [
            {
                "name": "Broken Rotation",
                "type": "weekly",
                "length": 1,
                "participants": [{"type": "user", "id": "u1"}],
                "startDate": "2024-01-01T00:00:00Z",
                "enabled": True,
                "timeRestriction": {
                    "type": "unknown-type",
                },
            }
        ],
    }
    oncall_schedules = []
    user_id_map = {"u1": "ou1"}

    match_schedule(schedule, oncall_schedules, user_id_map)
    assert schedule["migration_errors"]
    assert "Failed to parse schedule" in schedule["migration_errors"][0]


def test_match_schedule_invalid_day_becomes_migration_error():
    """An invalid day string should produce a migration error, not crash."""
    schedule = {
        "id": "s1",
        "name": "Bad Day Schedule",
        "timezone": "UTC",
        "rotations": [
            {
                "name": "Rotation",
                "type": "weekly",
                "length": 1,
                "participants": [{"type": "user", "id": "u1"}],
                "startDate": "2024-01-01T00:00:00Z",
                "enabled": True,
                "timeRestriction": {
                    "type": "weekday-and-time-of-day",
                    "restrictions": [
                        {
                            "startDay": "funday",
                            "endDay": "friday",
                            "startHour": 8,
                            "startMin": 0,
                            "endHour": 17,
                            "endMin": 0,
                        }
                    ],
                },
            }
        ],
    }
    oncall_schedules = []
    user_id_map = {"u1": "ou1"}

    match_schedule(schedule, oncall_schedules, user_id_map)
    assert schedule["migration_errors"]
    assert "Failed to parse schedule" in schedule["migration_errors"][0]


# ------------------------------------------------------------------
# Rotation.to_oncall_shifts — no restriction
# ------------------------------------------------------------------


def test_rotation_no_restriction():
    rotation = Rotation.from_dict(
        {
            "name": "Daily Rotation",
            "type": "daily",
            "length": 1,
            "participants": [{"type": "user", "id": "u1"}],
            "startDate": "2024-01-01T00:00:00Z",
        }
    )
    shifts = rotation.to_oncall_shifts({"u1": "ou1"})
    assert len(shifts) == 1
    assert shifts[0]["frequency"] == "daily"
    assert shifts[0]["interval"] == 1
    assert shifts[0]["duration"] == 86400
    assert "by_day" not in shifts[0]


# ------------------------------------------------------------------
# Rotation.to_oncall_shifts — time-of-day
# ------------------------------------------------------------------


def test_rotation_time_of_day():
    rotation = Rotation.from_dict(
        {
            "name": "Business Hours",
            "type": "daily",
            "length": 1,
            "participants": [{"type": "user", "id": "u1"}],
            "startDate": "2024-01-01T00:00:00Z",
            "timeRestriction": {
                "type": "time-of-day",
                "restriction": {
                    "startHour": 8,
                    "startMin": 0,
                    "endHour": 17,
                    "endMin": 0,
                },
            },
        }
    )
    shifts = rotation.to_oncall_shifts({"u1": "ou1"})
    assert len(shifts) == 1
    s = shifts[0]
    assert s["frequency"] == "daily"
    assert s["interval"] == 1
    assert s["duration"] == 9 * 3600
    assert s["start"] == "2024-01-01T08:00:00"
    assert "by_day" not in s


def test_rotation_time_of_day_weekly_adds_all_by_day():
    """A weekly rotation with time-of-day must set by_day to all 7 days."""
    rotation = Rotation.from_dict(
        {
            "name": "Weekly Business Hours",
            "type": "weekly",
            "length": 1,
            "participants": [{"type": "user", "id": "u1"}],
            "startDate": "2024-01-01T00:00:00Z",
            "timeRestriction": {
                "type": "time-of-day",
                "restriction": {
                    "startHour": 9,
                    "startMin": 0,
                    "endHour": 18,
                    "endMin": 0,
                },
            },
        }
    )
    shifts = rotation.to_oncall_shifts({"u1": "ou1"})
    assert len(shifts) == 1
    s = shifts[0]
    assert s["frequency"] == "weekly"
    assert s["interval"] == 1
    assert s["duration"] == 9 * 3600
    assert s["by_day"] == ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


# ------------------------------------------------------------------
# Rotation.to_oncall_shifts — weekday-and-time-of-day
# ------------------------------------------------------------------


def test_rotation_weekday_and_time_of_day_single():
    rotation = Rotation.from_dict(
        {
            "name": "Weekday Schedule",
            "type": "weekly",
            "length": 1,
            "participants": [{"type": "user", "id": "u1"}],
            "startDate": "2024-01-01T00:00:00Z",
            "timeRestriction": {
                "type": "weekday-and-time-of-day",
                "restrictions": [
                    {
                        "startDay": "monday",
                        "endDay": "friday",
                        "startHour": 8,
                        "startMin": 0,
                        "endHour": 17,
                        "endMin": 0,
                    }
                ],
            },
        }
    )
    shifts = rotation.to_oncall_shifts({"u1": "ou1"})
    assert len(shifts) == 1
    s = shifts[0]
    assert s["frequency"] == "weekly"
    assert s["interval"] == 1
    assert s["duration"] == 9 * 3600
    assert s["by_day"] == ["MO", "TU", "WE", "TH", "FR"]
    assert s["start"] == "2024-01-01T08:00:00"
    assert s["name"] == "Weekday Schedule"


def test_rotation_weekday_and_time_of_day_multiple_restrictions():
    rotation = Rotation.from_dict(
        {
            "name": "Split Schedule",
            "type": "weekly",
            "length": 2,
            "participants": [
                {"type": "user", "id": "u1"},
                {"type": "user", "id": "u2"},
            ],
            "startDate": "2024-01-01T00:00:00Z",
            "timeRestriction": {
                "type": "weekday-and-time-of-day",
                "restrictions": [
                    {
                        "startDay": "monday",
                        "endDay": "friday",
                        "startHour": 8,
                        "startMin": 0,
                        "endHour": 17,
                        "endMin": 0,
                    },
                    {
                        "startDay": "saturday",
                        "endDay": "sunday",
                        "startHour": 10,
                        "startMin": 0,
                        "endHour": 14,
                        "endMin": 0,
                    },
                ],
            },
        }
    )
    shifts = rotation.to_oncall_shifts({"u1": "ou1", "u2": "ou2"})
    assert len(shifts) == 2

    weekday_shift = shifts[0]
    assert weekday_shift["by_day"] == ["MO", "TU", "WE", "TH", "FR"]
    assert weekday_shift["duration"] == 9 * 3600
    assert weekday_shift["interval"] == 2
    assert weekday_shift["name"] == "Split Schedule-1"

    weekend_shift = shifts[1]
    assert weekend_shift["by_day"] == ["SA", "SU"]
    assert weekend_shift["duration"] == 4 * 3600
    assert weekend_shift["interval"] == 2
    assert weekend_shift["name"] == "Split Schedule-2"
    assert weekend_shift["rolling_users"] == [["ou1"], ["ou2"]]


# ------------------------------------------------------------------
# migrate_schedule
# ------------------------------------------------------------------


@patch("lib.opsgenie.resources.schedules.OnCallAPIClient")
def test_migrate_schedule(mock_client):
    mock_client.create.side_effect = [
        {"id": "or1"},  # First rotation shift
        {"id": "or2"},  # Second rotation shift (time-restricted)
        {"id": "os1", "name": "Primary Schedule"},  # Schedule creation
    ]

    schedule = {
        "id": "s1",
        "name": "Primary Schedule",
        "timezone": "UTC",
        "rotations": [
            {
                "name": "Daily Rotation",
                "type": "daily",
                "length": 1,
                "participants": [{"type": "user", "id": "u1"}],
                "startDate": "2024-01-01T00:00:00Z",
                "enabled": True,
            },
            {
                "name": "Weekly Rotation",
                "type": "weekly",
                "length": 1,
                "participants": [{"type": "user", "id": "u2"}],
                "startDate": "2024-01-01T00:00:00Z",
                "enabled": True,
                "timeRestriction": {
                    "type": "weekday-and-time-of-day",
                    "restrictions": [
                        {
                            "startDay": "monday",
                            "endDay": "friday",
                            "startHour": 9,
                            "startMin": 0,
                            "endHour": 17,
                            "endMin": 0,
                        }
                    ],
                },
            },
        ],
        "oncall_schedule": {"id": "os_old"},
    }
    user_id_map = {"u1": "ou1", "u2": "ou2"}

    migrate_schedule(schedule, user_id_map)

    mock_client.delete.assert_called_once_with("schedules/os_old")

    mock_client.create.assert_any_call(
        "on_call_shifts",
        {
            "name": "Daily Rotation",
            "type": "rolling_users",
            "time_zone": "UTC",
            "team_id": None,
            "level": 1,
            "start": "2024-01-01T00:00:00",
            "duration": 86400,
            "frequency": "daily",
            "interval": 1,
            "rolling_users": [["ou1"]],
            "start_rotation_from_user_index": 0,
            "week_start": "MO",
            "source": 0,
        },
    )

    mock_client.create.assert_any_call(
        "on_call_shifts",
        {
            "name": "Weekly Rotation",
            "type": "rolling_users",
            "time_zone": "UTC",
            "team_id": None,
            "level": 1,
            "start": "2024-01-01T09:00:00",
            "duration": 8 * 3600,
            "frequency": "weekly",
            "interval": 1,
            "by_day": ["MO", "TU", "WE", "TH", "FR"],
            "rolling_users": [["ou2"]],
            "start_rotation_from_user_index": 0,
            "week_start": "MO",
            "source": 0,
        },
    )

    mock_client.create.assert_called_with(
        "schedules",
        {
            "name": "Primary Schedule",
            "type": "web",
            "team_id": None,
            "time_zone": "UTC",
            "shifts": ["or1", "or2"],
        },
    )
