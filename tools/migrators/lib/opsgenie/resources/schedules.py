import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4

from lib.constants import ONCALL_SHIFT_WEB_SOURCE
from lib.oncall.api_client import OnCallAPIClient
from lib.opsgenie.config import (
    OPSGENIE_FILTER_SCHEDULE_REGEX,
    OPSGENIE_FILTER_TEAM,
    OPSGENIE_FILTER_USERS,
)
from lib.utils import dt_to_oncall_datetime, duration_to_frequency_and_interval

DAYS_OF_WEEK = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]
ONCALL_DAY_ABBREVS = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


def expand_day_range(start_day: str, end_day: str) -> list[str]:
    """Expand an OpsGenie day range (e.g. monday–friday) to OnCall day abbreviations."""
    start_idx = DAYS_OF_WEEK.index(start_day.lower())
    end_idx = DAYS_OF_WEEK.index(end_day.lower())
    if end_idx >= start_idx:
        indices = range(start_idx, end_idx + 1)
    else:
        indices = list(range(start_idx, 7)) + list(range(0, end_idx + 1))
    return [ONCALL_DAY_ABBREVS[i] for i in indices]


def calc_restriction_duration_seconds(restriction: dict) -> int:
    """Calculate the duration in seconds for a single time-restriction window."""
    start_minutes = restriction["startHour"] * 60 + restriction["startMin"]
    end_minutes = restriction["endHour"] * 60 + restriction["endMin"]
    if end_minutes > start_minutes:
        return (end_minutes - start_minutes) * 60
    # Overnight wrap-around
    return (24 * 60 - start_minutes + end_minutes) * 60


def filter_schedules(schedules: list[dict]) -> list[dict]:
    """Apply filters to schedules."""
    if OPSGENIE_FILTER_TEAM:
        filtered_schedules = []
        for s in schedules:
            if s["ownerTeam"]["id"] == OPSGENIE_FILTER_TEAM:
                filtered_schedules.append(s)
        schedules = filtered_schedules

    if OPSGENIE_FILTER_USERS:
        filtered_schedules = []
        for schedule in schedules:
            # Check if any rotation has a participant with ID in OPSGENIE_FILTER_USERS
            include_schedule = False
            for rotation in schedule.get("rotations", []):
                for participant in rotation.get("participants", []):
                    if (
                        participant.get("type") == "user"
                        and participant.get("id") in OPSGENIE_FILTER_USERS
                    ):
                        include_schedule = True
                        break
                if include_schedule:
                    break

            # Also check overrides for the filtered users
            if not include_schedule:
                for override in schedule.get("overrides", []):
                    if (
                        override.get("user", {}).get("type") == "user"
                        and override.get("user", {}).get("id") in OPSGENIE_FILTER_USERS
                    ):
                        include_schedule = True
                        break

            if include_schedule:
                filtered_schedules.append(schedule)

        schedules = filtered_schedules

    if OPSGENIE_FILTER_SCHEDULE_REGEX:
        pattern = re.compile(OPSGENIE_FILTER_SCHEDULE_REGEX)
        schedules = [s for s in schedules if pattern.match(s["name"])]

    return schedules


def match_schedule(
    schedule: dict, oncall_schedules: List[dict], user_id_map: Dict[str, str]
) -> None:
    """
    Match OpsGenie schedule with Grafana OnCall schedule.
    """
    oncall_schedule = None
    for candidate in oncall_schedules:
        if schedule["name"].lower().strip() == candidate["name"].lower().strip():
            oncall_schedule = candidate

    _, errors = Schedule.from_dict(schedule).to_oncall_schedule(user_id_map)
    schedule["migration_errors"] = errors
    schedule["oncall_schedule"] = oncall_schedule


def match_users_for_schedule(schedule: dict, users: List[dict]) -> None:
    """
    Match users referenced in schedule.
    """
    schedule["matched_users"] = []

    for rotation in schedule["rotations"]:
        for participant in rotation["participants"]:
            if participant["type"] == "user":
                for user in users:
                    if user["id"] == participant["id"] and user.get("oncall_user"):
                        schedule["matched_users"].append(user)


def migrate_schedule(schedule: dict, user_id_map: Dict[str, str]) -> None:
    """
    Migrate OpsGenie schedule to Grafana OnCall.
    """
    if schedule["oncall_schedule"]:
        OnCallAPIClient.delete(f"schedules/{schedule['oncall_schedule']['id']}")

    schedule["oncall_schedule"] = Schedule.from_dict(schedule).migrate(user_id_map)


@dataclass
class Schedule:
    """
    Utility class for converting an OpsGenie schedule to an OnCall schedule.
    An OpsGenie schedule has multiple rotations, each with a set of participants.
    """

    name: str
    timezone: str
    rotations: list["Rotation"]
    overrides: list["Override"]

    @classmethod
    def from_dict(cls, schedule: dict) -> "Schedule":
        """Create a Schedule object from an OpsGenie API response for a schedule."""
        rotations = []
        for rotation_dict in schedule["rotations"]:
            # Skip disabled rotations
            if not rotation_dict.get("enabled", True):
                continue
            rotations.append(Rotation.from_dict(rotation_dict))

        # Process overrides
        overrides = []
        for override_dict in schedule.get("overrides", []):
            overrides.append(Override.from_dict(override_dict))

        return cls(
            name=schedule["name"],
            timezone=schedule["timezone"],
            rotations=rotations,
            overrides=overrides,
        )

    def to_oncall_schedule(
        self, user_id_map: Dict[str, str]
    ) -> tuple[Optional[dict], list[str]]:
        """
        Convert a Schedule object to an OnCall schedule.
        Note that it also returns shifts, but these are not created at the same time as the schedule.
        """
        shifts = []
        errors = []

        for rotation in self.rotations:
            # Check if all users in the rotation exist in OnCall
            missing_user_ids = [
                p["id"]
                for p in rotation.participants
                if p["type"] == "user" and p["id"] not in user_id_map
            ]
            if missing_user_ids:
                errors.append(
                    f"{rotation.name}: Users with IDs {missing_user_ids} not found in OnCall."
                )
                continue

            shifts.extend(rotation.to_oncall_shifts(user_id_map))

        # Process overrides
        for override in self.overrides:
            # Check if the user exists in OnCall
            if override.user_id not in user_id_map:
                errors.append(
                    f"Override: User with ID '{override.user_id}' not found in OnCall."
                )
                continue

            shifts.append(override.to_oncall_override_shift(user_id_map))

        if errors:
            return None, errors

        return {
            "name": self.name,
            "type": "web",
            "team_id": None,
            "time_zone": self.timezone,
            "shifts": shifts,
        }, []

    def migrate(self, user_id_map: Dict[str, str]) -> dict:
        """
        Create an OnCall schedule and its shifts.
        First create the shifts, then create a schedule with shift IDs provided.
        """
        schedule, errors = self.to_oncall_schedule(user_id_map)
        assert not errors, "Unexpected errors: {}".format(errors)

        # Create shifts in OnCall
        shift_ids = []
        for shift in schedule["shifts"]:
            created_shift = OnCallAPIClient.create("on_call_shifts", shift)
            shift_ids.append(created_shift["id"])

        # Create schedule in OnCall with shift IDs provided
        schedule["shifts"] = shift_ids
        new_schedule = OnCallAPIClient.create("schedules", schedule)

        return new_schedule


@dataclass
class Override:
    """
    Utility class for representing a schedule override in OpsGenie.
    """

    start_date: datetime
    end_date: datetime
    user_id: str

    @classmethod
    def from_dict(cls, override: dict) -> "Override":
        """Create an Override object from an OpsGenie API response for a schedule override."""
        # Convert string dates to datetime objects
        start_date = datetime.fromisoformat(
            override["startDate"].replace("Z", "+00:00")
        )
        end_date = datetime.fromisoformat(override["endDate"].replace("Z", "+00:00"))

        # Extract user ID from the user object
        user_id = override.get("user", {}).get("id")

        if not user_id:
            raise ValueError(f"Could not extract user ID from override: {override}")

        return cls(
            start_date=start_date,
            end_date=end_date,
            user_id=user_id,
        )

    def to_oncall_override_shift(self, user_id_map: Dict[str, str]) -> dict:
        """Convert an Override object to an OnCall override shift."""
        duration = int((self.end_date - self.start_date).total_seconds())
        oncall_user_id = user_id_map[self.user_id]

        return {
            "name": f"Override-{uuid4().hex[:8]}",
            "type": "override",
            "team_id": None,
            "start": dt_to_oncall_datetime(self.start_date),
            "duration": duration,
            "rotation_start": dt_to_oncall_datetime(self.start_date),
            "users": [oncall_user_id],
            "time_zone": "UTC",
            "source": ONCALL_SHIFT_WEB_SOURCE,
        }


@dataclass
class TimeRestriction:
    """Parsed OpsGenie time restriction."""

    type: str
    restrictions: list[dict]

    @classmethod
    def from_dict(cls, data: dict) -> "TimeRestriction":
        restriction_type = data["type"]
        if restriction_type == "time-of-day":
            restrictions = [data["restriction"]]
        else:
            restrictions = data["restrictions"]
        return cls(type=restriction_type, restrictions=restrictions)


@dataclass
class Rotation:
    """
    Utility class for converting an OpsGenie rotation to an OnCall shift.
    """

    name: str
    type: str
    length: int
    start_date: datetime
    end_date: Optional[datetime]
    participants: List[dict]
    time_restriction: Optional[TimeRestriction] = field(default=None)

    @classmethod
    def from_dict(cls, rotation: dict) -> "Rotation":
        """Create a Rotation object from an OpsGenie API response for a rotation."""
        start_date = datetime.fromisoformat(
            rotation["startDate"].replace("Z", "+00:00")
        )

        end_date = None
        if rotation.get("endDate"):
            end_date = datetime.fromisoformat(
                rotation["endDate"].replace("Z", "+00:00")
            )

        time_restriction = None
        if rotation.get("timeRestriction"):
            time_restriction = TimeRestriction.from_dict(rotation["timeRestriction"])

        return cls(
            name=rotation["name"],
            type=rotation["type"],
            length=rotation["length"],
            start_date=start_date,
            end_date=end_date,
            participants=rotation["participants"],
            time_restriction=time_restriction,
        )

    def to_oncall_shifts(self, user_id_map: Dict[str, str]) -> list[dict]:
        """Convert a Rotation to one or more OnCall shifts.

        Time restrictions may produce multiple shifts (one per restriction
        window in the weekday-and-time-of-day case).
        """
        if self.time_restriction is None:
            return [self._build_base_shift(user_id_map)]

        if self.time_restriction.type == "time-of-day":
            r = self.time_restriction.restrictions[0]
            return [self._build_time_of_day_shift(user_id_map, r)]

        shifts = []
        for idx, r in enumerate(self.time_restriction.restrictions):
            suffix = f"-{idx + 1}" if len(self.time_restriction.restrictions) > 1 else ""
            shifts.append(self._build_weekday_time_shift(user_id_map, r, suffix))
        return shifts

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _rolling_users(self, user_id_map: Dict[str, str]) -> list[list[str]]:
        return [
            [user_id_map[p["id"]]]
            for p in self.participants
            if p["type"] == "user" and p["id"] in user_id_map
        ]

    def _base_duration(self) -> timedelta:
        if self.type == "daily":
            return timedelta(days=self.length)
        elif self.type == "weekly":
            return timedelta(weeks=self.length)
        elif self.type == "hourly":
            return timedelta(hours=self.length)
        return timedelta(days=self.length)

    def _apply_common_fields(self, shift: dict) -> dict:
        if self.end_date:
            shift["until"] = dt_to_oncall_datetime(self.end_date)
        return shift

    def _build_base_shift(self, user_id_map: Dict[str, str]) -> dict:
        """Shift without any time restriction."""
        base_duration = self._base_duration()
        frequency, interval = duration_to_frequency_and_interval(base_duration)

        shift = {
            "name": self.name or uuid4().hex,
            "type": "rolling_users",
            "time_zone": "UTC",
            "team_id": None,
            "level": 1,
            "start": dt_to_oncall_datetime(self.start_date),
            "duration": int(base_duration.total_seconds()),
            "frequency": frequency,
            "interval": interval,
            "rolling_users": self._rolling_users(user_id_map),
            "start_rotation_from_user_index": 0,
            "week_start": "MO",
            "source": ONCALL_SHIFT_WEB_SOURCE,
        }
        return self._apply_common_fields(shift)

    def _restricted_start(self, restriction: dict) -> datetime:
        """Return the rotation start_date with time overridden by the restriction."""
        return self.start_date.replace(
            hour=restriction["startHour"],
            minute=restriction["startMin"],
            second=0,
            microsecond=0,
        )

    def _build_time_of_day_shift(
        self, user_id_map: Dict[str, str], restriction: dict
    ) -> dict:
        """Shift for a time-of-day restriction (same hours every day)."""
        base_duration = self._base_duration()
        frequency, interval = duration_to_frequency_and_interval(base_duration)
        duration = calc_restriction_duration_seconds(restriction)

        shift = {
            "name": self.name or uuid4().hex,
            "type": "rolling_users",
            "time_zone": "UTC",
            "team_id": None,
            "level": 1,
            "start": dt_to_oncall_datetime(self._restricted_start(restriction)),
            "duration": duration,
            "frequency": frequency,
            "interval": interval,
            "rolling_users": self._rolling_users(user_id_map),
            "start_rotation_from_user_index": 0,
            "week_start": "MO",
            "source": ONCALL_SHIFT_WEB_SOURCE,
        }
        return self._apply_common_fields(shift)

    def _build_weekday_time_shift(
        self, user_id_map: Dict[str, str], restriction: dict, suffix: str = ""
    ) -> dict:
        """Shift for a weekday-and-time-of-day restriction window."""
        by_day = expand_day_range(restriction["startDay"], restriction["endDay"])
        duration = calc_restriction_duration_seconds(restriction)

        if self.type == "weekly":
            interval = self.length
        else:
            interval = 1

        name = self.name or uuid4().hex
        if suffix:
            name = f"{name}{suffix}"

        shift = {
            "name": name,
            "type": "rolling_users",
            "time_zone": "UTC",
            "team_id": None,
            "level": 1,
            "start": dt_to_oncall_datetime(self._restricted_start(restriction)),
            "duration": duration,
            "frequency": "weekly",
            "interval": interval,
            "by_day": by_day,
            "rolling_users": self._rolling_users(user_id_map),
            "start_rotation_from_user_index": 0,
            "week_start": "MO",
            "source": ONCALL_SHIFT_WEB_SOURCE,
        }
        return self._apply_common_fields(shift)
