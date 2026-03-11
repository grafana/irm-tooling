from lib.oncall_oss.resources.users import match_user


def test_match_user_by_email():
    user = {"email": "admin@localhost", "username": "admin"}
    oncall_users = [{"email": "admin@localhost", "username": "admin"}]

    match_user(user, oncall_users)

    assert user["oncall_user"] == oncall_users[0]


def test_match_user_by_username_when_email_differs():
    user = {"email": "source@example.com", "username": "admin"}
    oncall_users = [{"email": "target@example.com", "username": "admin"}]

    match_user(user, oncall_users)

    assert user["oncall_user"] == oncall_users[0]


def test_match_user_no_match():
    user = {"email": "one@example.com", "username": "one"}
    oncall_users = [{"email": "two@example.com", "username": "two"}]

    match_user(user, oncall_users)

    assert user["oncall_user"] is None
