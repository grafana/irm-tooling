import os

from lib.base_config import *  # noqa: F401,F403

JSM_EMAIL = os.environ["JSM_EMAIL"]
JSM_API_TOKEN = os.environ["JSM_API_TOKEN"]
JSM_CLOUD_ID = os.environ["JSM_CLOUD_ID"]
JSM_API_BASE_URL = (
    f"https://api.atlassian.com/jsm/ops/api/{JSM_CLOUD_ID}/v1/"
)

JSM_TO_ONCALL_CONTACT_METHOD_MAP = {
    "sms": "notify_by_sms",
    "voice": "notify_by_phone_call",
    "email": "notify_by_email",
    "mobile": "notify_by_mobile_app",
}

JSM_TO_ONCALL_VENDOR_MAP = {
    "AmazonCloudWatch": "amazon_sns",
    "AmazonRds": "amazon_sns",
    "AmazonSns": "amazon_sns",
    "AppDynamics": "appdynamics",
    "Datadog": "datadog",
    "Email": "inbound_email",
    "Jira": "jira",
    "JiraServiceDesk": "jira",
    "Kapacitor": "kapacitor",
    "NewRelic": "newrelic",
    "NewRelicV2": "newrelic",
    "Pingdom": "pingdom",
    "PingdomV2": "pingdom",
    "Prometheus": "alertmanager",
    "Prtg": "prtg",
    "Scout": "webhook",
    "Sentry": "sentry",
    "Stackdriver": "stackdriver",
    "UptimeRobot": "uptimerobot",
    "Webhook": "webhook",
    "Zabbix": "zabbix",
}

UNSUPPORTED_INTEGRATION_TO_WEBHOOKS = (
    os.getenv("UNSUPPORTED_INTEGRATION_TO_WEBHOOKS", "false").lower() == "true"
)

MIGRATE_USERS = os.getenv("MIGRATE_USERS", "true").lower() == "true"

JSM_FILTER_TEAM = os.getenv("JSM_FILTER_TEAM")

JSM_FILTER_SCHEDULE_REGEX = os.getenv("JSM_FILTER_SCHEDULE_REGEX")
JSM_FILTER_ESCALATION_REGEX = os.getenv("JSM_FILTER_ESCALATION_REGEX")
JSM_FILTER_INTEGRATION_REGEX = os.getenv("JSM_FILTER_INTEGRATION_REGEX")

PRESERVE_EXISTING_USER_NOTIFICATION_RULES = (
    os.getenv("PRESERVE_EXISTING_USER_NOTIFICATION_RULES", "true").lower() == "true"
)
