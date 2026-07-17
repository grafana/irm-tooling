from lib.jsm.resources.schedules import _normalize_schedule, match_schedule


def test_normalize_schedule_maps_jsm_fields():
    schedule = {
        "name": "Primary",
        "timezone": "UTC",
        "rotations": [
            {
                "name": "Daily",
                "type": "daily",
                "length": 1,
                "startDate": "2024-01-01T00:00:00Z",
                "participants": [{"type": "user", "id": "u1"}],
            }
        ],
    }
    normalized = _normalize_schedule(schedule)
    assert normalized["timezone"] == "UTC"
    assert normalized["rotations"][0]["startDate"] == "2024-01-01T00:00:00Z"


def test_match_schedule_sets_errors_on_invalid_restriction():
    schedule = {
        "name": "Broken",
        "timezone": "UTC",
        "rotations": [
            {
                "name": "R1",
                "type": "daily",
                "length": 1,
                "startDate": "2024-01-01T00:00:00Z",
                "participants": [{"type": "user", "id": "u1"}],
                "timeRestriction": {"type": "unsupported"},
            }
        ],
    }
    match_schedule(schedule, [], {"u1": "ou1"})
    assert schedule["migration_errors"]
