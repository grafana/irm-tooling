from lib.common.resources.users import match_user as _match_user_by_email


def match_user(user: dict, oncall_users: list[dict]) -> None:
    """Match JSM user to target IRM user by email."""
    if not user.get("email"):
        user["email"] = user.get("username", "")
    _match_user_by_email(user, oncall_users)
