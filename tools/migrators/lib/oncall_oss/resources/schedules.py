"""
Migrate schedules and on-call shifts from OnCall OSS to IRM.
Same API shape; we remap user IDs in shifts.
"""

from typing import Dict, List

from lib.oncall.api_client import OnCallAPIClient


def match_schedule(schedule: dict, oncall_schedules: List[dict]) -> None:
    """Match OSS schedule to target schedule by name (case-insensitive)."""
    oncall_schedule = None
    for candidate in oncall_schedules:
        if (schedule.get("name") or "").lower().strip() == (
            candidate.get("name") or ""
        ).lower().strip():
            oncall_schedule = candidate
            break
    schedule["oncall_schedule"] = oncall_schedule


def _remap_shift(shift: dict, user_id_map: Dict[str, str]) -> dict | None:
    """Build create payload for one shift with user IDs remapped. Returns None if unmapped users."""
    payload = {k: v for k, v in shift.items() if k not in ("id", "schedule_id")}

    if shift.get("type") == "override" and "users" in shift:
        new_users = [user_id_map[uid] for uid in shift["users"] if uid in user_id_map]
        if not new_users:
            return None
        payload["users"] = new_users
    elif "rolling_users" in shift:
        new_rolling = []
        for slot in shift["rolling_users"]:
            new_slot = [user_id_map[uid] for uid in slot if uid in user_id_map]
            if not new_slot:
                return None
            new_rolling.append(new_slot)
        payload["rolling_users"] = new_rolling
    elif "users" in shift:
        new_users = [user_id_map[uid] for uid in shift["users"] if uid in user_id_map]
        if not new_users:
            return None
        payload["users"] = new_users

    return payload


def migrate_schedule(
    schedule: dict,
    shifts: List[dict],
    user_id_map: Dict[str, str],
) -> dict:
    """Create or replace schedule and its shifts in target IRM."""
    if schedule.get("oncall_schedule"):
        OnCallAPIClient.delete(f"schedules/{schedule['oncall_schedule']['id']}")

    schedule_payload = {
        "name": schedule.get("name") or "Migrated schedule",
        "type": schedule.get("type") or "web",
        "time_zone": schedule.get("time_zone") or "UTC",
        "team_id": schedule.get("team_id"),
    }
    if schedule_payload["team_id"] is None:
        schedule_payload["team_id"] = None

    shift_ids = []
    for shift in shifts:
        payload = _remap_shift(shift, user_id_map)
        if payload is not None:
            created = OnCallAPIClient.create("on_call_shifts", payload)
            shift_ids.append(created["id"])

    schedule_payload["shifts"] = shift_ids
    new_schedule = OnCallAPIClient.create("schedules", schedule_payload)
    schedule["oncall_schedule"] = new_schedule
    return new_schedule
