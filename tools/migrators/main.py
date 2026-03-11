from lib.base_config import MIGRATING_FROM, ONCALL_OSS, OPSGENIE, PAGERDUTY, SPLUNK

if __name__ == "__main__":
    if MIGRATING_FROM == PAGERDUTY:
        from lib.pagerduty.migrate import migrate

        migrate()
    elif MIGRATING_FROM == SPLUNK:
        from lib.splunk.migrate import migrate

        migrate()
    elif MIGRATING_FROM == OPSGENIE:
        from lib.opsgenie.migrate import migrate

        migrate()
    elif MIGRATING_FROM == ONCALL_OSS:
        from lib.oncall_oss.migrate import migrate

        migrate()
    else:
        raise ValueError("Invalid MIGRATING_FROM value")
