"""Report formatting for OnCall OSS migration."""

from lib.common.report import ERROR_SIGN, SUCCESS_SIGN, TAB, WARNING_SIGN


def format_user(user: dict) -> str:
    return f"{user.get('username', user.get('email', '?'))}"


def format_schedule(schedule: dict) -> str:
    return schedule.get("name") or "Unnamed schedule"


def format_escalation_chain(chain: dict) -> str:
    return chain.get("name") or "Unnamed chain"


def format_integration(integration: dict) -> str:
    return integration.get("name") or "Unnamed integration"


def user_report(users: list[dict]) -> str:
    report = ["User report:"]
    for user in users:
        if user.get("oncall_user"):
            report.append(f"{TAB}{SUCCESS_SIGN} {format_user(user)}")
        else:
            report.append(
                f"{TAB}{ERROR_SIGN} {format_user(user)} — no matching user in target IRM"
            )
    return "\n".join(report)


def schedule_report(schedules: list[dict]) -> str:
    report = ["Schedule report:"]
    for schedule in schedules:
        if schedule.get("oncall_schedule"):
            report.append(
                f"{TAB}{WARNING_SIGN} {format_schedule(schedule)} (existing schedule will be replaced)"
            )
        else:
            report.append(f"{TAB}{SUCCESS_SIGN} {format_schedule(schedule)}")
    return "\n".join(report)


def escalation_chain_report(chains: list[dict]) -> str:
    report = ["Escalation chain report:"]
    for chain in chains:
        if chain.get("oncall_escalation_chain"):
            report.append(
                f"{TAB}{WARNING_SIGN} {format_escalation_chain(chain)} (existing chain will be replaced)"
            )
        else:
            report.append(f"{TAB}{SUCCESS_SIGN} {format_escalation_chain(chain)}")
    return "\n".join(report)


def integration_report(integrations: list[dict]) -> str:
    report = ["Integration report:"]
    for integration in integrations:
        if integration.get("oncall_integration"):
            report.append(
                f"{TAB}{WARNING_SIGN} {format_integration(integration)} (existing integration will be replaced)"
            )
        else:
            report.append(f"{TAB}{SUCCESS_SIGN} {format_integration(integration)}")
    return "\n".join(report)
