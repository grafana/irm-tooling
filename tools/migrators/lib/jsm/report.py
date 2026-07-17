from lib.common.report import ERROR_SIGN, SUCCESS_SIGN, TAB, WARNING_SIGN
from lib.jsm.config import (
    PRESERVE_EXISTING_USER_NOTIFICATION_RULES,
    UNSUPPORTED_INTEGRATION_TO_WEBHOOKS,
)
from lib.opsgenie.resources.escalation_policies import determine_policy_name


def format_user(user: dict) -> str:
    return f"{user.get('fullName', user.get('username', '?'))} ({user.get('email', user.get('username', '?'))})"


def format_schedule(schedule: dict) -> str:
    return schedule["name"]


def format_escalation(escalation: dict) -> str:
    policy = escalation.get("_normalized_policy", escalation)
    return determine_policy_name(policy)


def format_integration(integration: dict) -> str:
    team_name = integration.get("teamName")
    if team_name:
        return f"{integration['name']} ({integration['type']}) [team: {team_name}]"
    return f"{integration['name']} ({integration['type']})"


def user_report(users: list[dict]) -> str:
    report = ["User notification rules report:"]
    for user in users:
        if user.get("oncall_user"):
            if (
                user["oncall_user"]["notification_rules"]
                and PRESERVE_EXISTING_USER_NOTIFICATION_RULES
            ):
                report.append(
                    f"{TAB}{WARNING_SIGN} {format_user(user)} (existing notification rules will be preserved)"
                )
            elif (
                user["oncall_user"]["notification_rules"]
                and not PRESERVE_EXISTING_USER_NOTIFICATION_RULES
            ):
                report.append(
                    f"{TAB}{WARNING_SIGN} {format_user(user)} (existing notification rules will be deleted)"
                )
            else:
                report.append(f"{TAB}{SUCCESS_SIGN} {format_user(user)}")
        else:
            report.append(
                f"{TAB}{ERROR_SIGN} {format_user(user)} — no Grafana IRM user found with this email"
            )
    return "\n".join(report)


def schedule_report(schedules: list[dict]) -> str:
    report = ["Schedule report:"]
    for schedule in schedules:
        if schedule.get("migration_errors"):
            errors = schedule["migration_errors"]
            error_msg = " — " + errors[0] if len(errors) == 1 else " —"
            report.append(f"{TAB}{ERROR_SIGN} {format_schedule(schedule)}{error_msg}")
            if len(errors) > 1:
                for error in errors:
                    report.append(f"{TAB}{TAB}- {error}")
        elif schedule.get("unmatched_users"):
            report.append(
                f"{TAB}{ERROR_SIGN} {format_schedule(schedule)} — schedule references unmatched users"
            )
            for user in schedule["unmatched_users"]:
                report.append(
                    f"{TAB}{TAB}{ERROR_SIGN} {format_user(user)} — no Grafana IRM user found with this email"
                )
        elif schedule.get("oncall_schedule"):
            report.append(
                f"{TAB}{WARNING_SIGN} {format_schedule(schedule)} (existing schedule will be deleted)"
            )
        else:
            report.append(f"{TAB}{SUCCESS_SIGN} {format_schedule(schedule)}")
    return "\n".join(report)


def escalation_report(escalations: list[dict]) -> str:
    report = ["Escalation policy report:"]
    for escalation in escalations:
        policy = escalation.get("_normalized_policy", escalation)
        if all(
            rule.get("notifyType") != "default" for rule in policy.get("rules", [])
        ):
            report.append(
                f"{TAB}{WARNING_SIGN} {format_escalation(escalation)} — will be skipped (all rules have a non-default notifyType)"
            )
        elif escalation.get("oncall_escalation_chain"):
            report.append(
                f"{TAB}{WARNING_SIGN} {format_escalation(escalation)} (existing escalation chain will be deleted)"
            )
        else:
            report.append(f"{TAB}{SUCCESS_SIGN} {format_escalation(escalation)}")
    return "\n".join(report)


def integration_report(integrations: list[dict]) -> str:
    report = ["Integration report:"]
    for integration in integrations:
        if integration.get("oncall_integration"):
            report.append(
                f"{TAB}{WARNING_SIGN} {format_integration(integration)} (existing integration will be deleted)"
            )
        elif (
            not integration.get("oncall_type")
            and not UNSUPPORTED_INTEGRATION_TO_WEBHOOKS
        ):
            report.append(
                f"{TAB}{ERROR_SIGN} {format_integration(integration)} — unsupported integration type"
            )
        elif not integration.get("oncall_type") and UNSUPPORTED_INTEGRATION_TO_WEBHOOKS:
            report.append(
                f"{TAB}{WARNING_SIGN} {format_integration(integration)} — unsupported integration type, will be migrated as webhook"
            )
        else:
            report.append(f"{TAB}{SUCCESS_SIGN} {format_integration(integration)}")
    return "\n".join(report)
