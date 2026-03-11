"""
Orchestrate migration from Grafana OnCall OSS to Grafana Cloud IRM.
Fetches resources from OSS, matches to target, then migrates in dependency order.
"""

from collections import defaultdict

from lib.common.report import TAB
from lib.oncall.api_client import OnCallAPIClient
from lib.oncall_oss.config import (
    MIGRATE_USERS,
    MODE,
    MODE_PLAN,
    ONCALL_OSS_API_TOKEN,
    ONCALL_OSS_API_URL,
)
from lib.oncall_oss.report import (
    escalation_chain_report,
    format_escalation_chain,
    format_integration,
    format_schedule,
    format_user,
    format_webhook,
    integration_report,
    schedule_report,
    user_report,
    webhook_report,
)
from lib.oncall_oss.resources.escalation_chains import (
    match_escalation_chain,
    migrate_escalation_chain,
)
from lib.oncall_oss.resources.integrations import (
    is_system_managed_integration,
    match_integration,
    migrate_integration,
)
from lib.oncall_oss.resources.notification_rules import migrate_notification_rules
from lib.oncall_oss.resources.schedules import (
    match_schedule,
    migrate_schedule,
)
from lib.oncall_oss.resources.users import match_user
from lib.oncall_oss.resources.webhooks import (
    match_webhook,
    migrate_webhook,
)


def migrate() -> None:
    source = OnCallAPIClient(ONCALL_OSS_API_URL, ONCALL_OSS_API_TOKEN, "oncall_oss")

    print("▶ Fetching users from OSS...")
    users = source.list_users_with_notification_rules()

    print("▶ Fetching target users...")
    oncall_users = OnCallAPIClient.list_users_with_notification_rules()

    print("▶ Fetching escalation chains from OSS...")
    chains = source.list_escalation_chains()
    all_policies = source.list_escalation_policies()
    policies_by_chain = defaultdict(list)
    for p in all_policies:
        policies_by_chain[p["escalation_chain_id"]].append(p)

    print("▶ Fetching schedules and shifts from OSS...")
    schedules = source.list_schedules()
    all_shifts = source.list_on_call_shifts()
    shifts_by_schedule = defaultdict(list)
    for shift in all_shifts:
        sid = shift.get("schedule") or shift.get("schedule_id")
        if sid is not None:
            shifts_by_schedule[sid].append(shift)

    print("▶ Fetching integrations and routes from OSS...")
    integrations = source.list_integrations()
    all_routes = source.list_routes()
    routes_by_integration = defaultdict(list)
    for route in all_routes:
        iid = route.get("integration_id")
        if iid is not None:
            routes_by_integration[iid].append(route)

    print("▶ Fetching outgoing webhooks from OSS...")
    webhooks = source.list_webhooks()

    print("▶ Fetching target resources...")
    oncall_chains = OnCallAPIClient.list_all("escalation_chains")
    oncall_schedules = OnCallAPIClient.list_all("schedules")
    oncall_integrations = OnCallAPIClient.list_all("integrations")
    oncall_webhooks = OnCallAPIClient.list_all("webhooks")

    print("\n▶ Matching users...")
    for user in users:
        match_user(user, oncall_users)
    print(user_report(users))

    user_id_map = {
        u["id"]: u["oncall_user"]["id"] for u in users if u.get("oncall_user")
    }

    print("\n▶ Matching schedules...")
    for schedule in schedules:
        match_schedule(schedule, oncall_schedules)
    print(schedule_report(schedules))

    print("\n▶ Matching escalation chains...")
    for chain in chains:
        match_escalation_chain(chain, oncall_chains)
    print(escalation_chain_report(chains))

    print("\n▶ Matching integrations...")
    for integration in integrations:
        match_integration(integration, oncall_integrations)
    print(integration_report(integrations))

    print("\n▶ Matching outgoing webhooks...")
    for webhook in webhooks:
        match_webhook(webhook, oncall_webhooks)
    print(webhook_report(webhooks))

    if MODE == MODE_PLAN:
        return

    schedule_id_map = {}
    print("\n▶ Migrating schedules...")
    for schedule in schedules:
        print(f"{TAB}Migrating {format_schedule(schedule)}...")
        shifts = shifts_by_schedule.get(schedule["id"], [])
        new_schedule = migrate_schedule(schedule, shifts, user_id_map)
        schedule_id_map[schedule["id"]] = new_schedule["id"]

    chain_id_map = {}
    print("\n▶ Migrating escalation chains...")
    for chain in chains:
        print(f"{TAB}Migrating {format_escalation_chain(chain)}...")
        policies = policies_by_chain.get(chain["id"], [])
        new_chain = migrate_escalation_chain(
            chain, policies, user_id_map, schedule_id_map
        )
        chain_id_map[chain["id"]] = new_chain["id"]

    print("\n▶ Migrating integrations...")
    for integration in integrations:
        if integration.get("migration_errors"):
            print(
                f"{TAB}⏭ Skipping {format_integration(integration)}: "
                + "; ".join(integration["migration_errors"])
            )
            continue
        routes = routes_by_integration.get(integration["id"], [])
        if is_system_managed_integration(integration):
            print(f"{TAB}Updating routes on {format_integration(integration)}...")
        else:
            print(f"{TAB}Migrating {format_integration(integration)}...")
        migrate_integration(integration, routes, chain_id_map)

    print("\n▶ Migrating outgoing webhooks...")
    for webhook in webhooks:
        print(f"{TAB}Migrating {format_webhook(webhook)}...")
        migrate_webhook(webhook)

    if MIGRATE_USERS:
        print("\n▶ Migrating user notification rules...")
        for user in users:
            if user.get("oncall_user"):
                print(f"{TAB}Migrating {format_user(user)}...")
                migrate_notification_rules(user, user_id_map)
