"""User matching helpers for OnCall OSS migrations."""

from typing import List


def _identity_values(user: dict) -> set[str]:
    values = set()
    for field in ("email", "username"):
        value = user.get(field)
        if isinstance(value, str):
            normalized = value.lower().strip()
            if normalized:
                values.add(normalized)
    return values


def match_user(user: dict, oncall_users: List[dict]) -> None:
    """Match source and target users by email or username."""
    source_values = _identity_values(user)
    oncall_user = None

    for candidate_user in oncall_users:
        if source_values & _identity_values(candidate_user):
            oncall_user = candidate_user
            break

    user["oncall_user"] = oncall_user
