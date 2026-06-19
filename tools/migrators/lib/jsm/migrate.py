from lib.common.report import TAB
from lib.jsm.api_client import JsmAPIClient
from lib.jsm.config import MIGRATE_USERS, MODE, MODE_PLAN, UNSUPPORTED_INTEGRATION_TO_WEBHOOKS
from lib.jsm.report import (
    escalation_report,
    format_escalation,
    format_integration,
    format_schedule,
    format_user,
    integration_report,
    schedule_report,
    user_report,
)
from lib.jsm.resources.escalation_chains import (
    filter_escalations,
    match_users_and_schedules_for_escalation,
    migrate_escalation,
    normalize_and_match_escalation,
)
from lib.jsm.resources.integrations import (
    filter_integrations,
    match_integration,
    migrate_integration,
)
from lib.jsm.resources.notification_rules import migrate_notification_rules
from lib.jsm.resources.schedules import (
    filter_schedules,
    match_schedule,
    match_users_for_schedule,
    migrate_schedule,
)
from lib.jsm.resources.users import match_user
from lib.oncall.api_client import OnCallAPIClient


def migrate() -> None:
    client = JsmAPIClient()

    print("▶ Fetching teams...")
    teams = client.list_teams()
    team_name_map = {t["id"]: t.get("name", t["id"]) for t in teams}

    print("▶ Fetching schedules...")
    schedules = client.list_schedules()
    schedules = filter_schedules(schedules)
    oncall_schedules = OnCallAPIClient.list_all("schedules")

    print("▶ Fetching escalation policies...")
    escalations = client.list_all_escalations()
    escalations = filter_escalations(escalations)
    oncall_escalation_chains = OnCallAPIClient.list_all("escalation_chains")

    print("▶ Fetching integrations...")
    integrations = client.list_integrations()
    integrations = filter_integrations(integrations)
    for integration in integrations:
        team_id = integration.get("teamId")
        if team_id and team_id in team_name_map:
            integration["teamName"] = team_name_map[team_id]
    oncall_integrations = OnCallAPIClient.list_all("integrations")

    notification_rules = []
    if MIGRATE_USERS:
        print("▶ Fetching notification rules...")
        notification_rules = client.list_notification_rules()

    users = client.list_users_from_resources(schedules, escalations, notification_rules)

    if MIGRATE_USERS:
        print("▶ Fetching target users...")
        oncall_users = OnCallAPIClient.list_users_with_notification_rules()
    else:
        print("▶ Skipping user migration as MIGRATE_USERS is false...")
        oncall_users = []

    if MIGRATE_USERS:
        print("\n▶ Matching users...")
        for user in users:
            match_user(user, oncall_users)
        print(user_report(users))

    user_id_map = {
        u["id"]: u["oncall_user"]["id"] for u in users if u.get("oncall_user")
    }

    print("\n▶ Matching schedules...")
    for schedule in schedules:
        match_schedule(schedule, oncall_schedules, user_id_map)
        match_users_for_schedule(schedule, users)
    print(schedule_report(schedules))

    print("\n▶ Matching escalation policies...")
    for escalation in escalations:
        normalize_and_match_escalation(escalation, oncall_escalation_chains)
        match_users_and_schedules_for_escalation(escalation, users, schedules)
    print(escalation_report(escalations))

    print("\n▶ Matching integrations...")
    for integration in integrations:
        match_integration(integration, oncall_integrations)
    print(integration_report(integrations))

    if MODE == MODE_PLAN:
        return

    if MIGRATE_USERS:
        print("\n▶ Migrating user notification rules...")
        for user in users:
            if user.get("oncall_user") and user.get("notification_rules"):
                print(f"{TAB}Migrating {format_user(user)}...")
                migrate_notification_rules(user)

    print("\n▶ Migrating schedules...")
    for schedule in schedules:
        if not schedule.get("migration_errors") and not schedule.get("unmatched_users"):
            print(f"{TAB}Migrating {format_schedule(schedule)}...")
            migrate_schedule(schedule, user_id_map)

    print("\n▶ Migrating escalation policies...")
    for escalation in escalations:
        policy = escalation.get("_normalized_policy", escalation)
        if all(rule.get("notifyType") != "default" for rule in policy.get("rules", [])):
            print(
                f"{TAB}Skipping migrating {format_escalation(escalation)} because all of its rules "
                "have a non-default notifyType"
            )
            continue
        print(f"{TAB}Migrating {format_escalation(escalation)}...")
        migrate_escalation(escalation, users, schedules)

    print("\n▶ Migrating integrations...")
    for integration in integrations:
        print(f"{TAB}Migrating {format_integration(integration)}...")
        if (
            integration.get("oncall_type") is None
            and not UNSUPPORTED_INTEGRATION_TO_WEBHOOKS
        ):
            print(
                f"{TAB}Skipping {format_integration(integration)} because it is not supported "
                "and UNSUPPORTED_INTEGRATION_TO_WEBHOOKS is false"
            )
            continue
        migrate_integration(integration, escalations)
