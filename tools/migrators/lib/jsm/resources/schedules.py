import re
from typing import Dict, List

from lib.jsm.config import JSM_FILTER_SCHEDULE_REGEX, JSM_FILTER_TEAM
from lib.opsgenie.resources.schedules import Schedule


def filter_schedules(schedules: list[dict]) -> list[dict]:
    if JSM_FILTER_TEAM:
        schedules = [s for s in schedules if s.get("teamId") == JSM_FILTER_TEAM]

    if JSM_FILTER_SCHEDULE_REGEX:
        pattern = re.compile(JSM_FILTER_SCHEDULE_REGEX)
        schedules = [s for s in schedules if pattern.match(s.get("name", ""))]

    return schedules


def _normalize_schedule(schedule: dict) -> dict:
    """Convert JSM schedule payload to Opsgenie-compatible shape for reuse."""
    rotations = []
    for rotation in schedule.get("rotations", []):
        rotations.append(
            {
                "name": rotation.get("name", "Rotation"),
                "type": rotation.get("type", "daily"),
                "length": rotation.get("length", 1),
                "startDate": rotation["startDate"],
                "endDate": rotation.get("endDate"),
                "participants": rotation.get("participants", []),
                "timeRestriction": rotation.get("timeRestriction"),
                "enabled": rotation.get("enabled", schedule.get("enabled", True)),
            }
        )

    return {
        "name": schedule["name"],
        "timezone": schedule.get("timezone", "UTC"),
        "rotations": rotations,
        "overrides": schedule.get("overrides", []),
    }


def match_schedule(
    schedule: dict, oncall_schedules: List[dict], user_id_map: Dict[str, str]
) -> None:
    oncall_schedule = None
    for candidate in oncall_schedules:
        if schedule["name"].lower().strip() == candidate["name"].lower().strip():
            oncall_schedule = candidate

    try:
        _, errors = Schedule.from_dict(_normalize_schedule(schedule)).to_oncall_schedule(
            user_id_map
        )
    except (ValueError, KeyError, TypeError) as exc:
        errors = [f"Failed to parse schedule: {exc}"]

    schedule["migration_errors"] = errors
    schedule["oncall_schedule"] = oncall_schedule


def match_users_for_schedule(schedule: dict, users: List[dict]) -> None:
    schedule["unmatched_users"] = []
    user_ids_with_match = {u["id"] for u in users if u.get("oncall_user")}

    for rotation in schedule.get("rotations", []):
        for participant in rotation.get("participants", []):
            if (
                participant.get("type") == "user"
                and participant["id"] not in user_ids_with_match
            ):
                for user in users:
                    if user["id"] == participant["id"] and not user.get("oncall_user"):
                        if user not in schedule["unmatched_users"]:
                            schedule["unmatched_users"].append(user)


def migrate_schedule(schedule: dict, user_id_map: Dict[str, str]) -> None:
    schedule["oncall_schedule"] = Schedule.from_dict(
        _normalize_schedule(schedule)
    ).migrate(user_id_map)
