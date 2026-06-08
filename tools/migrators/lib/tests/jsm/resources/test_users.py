from lib.jsm.resources.users import match_user


def test_match_user_by_email():
    user = {"id": "u1", "email": "alice@example.com"}
    oncall_users = [{"id": "ou1", "email": "alice@example.com"}]
    match_user(user, oncall_users)
    assert user["oncall_user"]["id"] == "ou1"
