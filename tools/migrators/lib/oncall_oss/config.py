import os
from urllib.parse import urljoin

from lib.base_config import *  # noqa: F401,F403

ONCALL_OSS_API_URL = urljoin(
    os.environ["ONCALL_OSS_API_URL"].removesuffix("/") + "/",
    "api/v1/",
)
ONCALL_OSS_API_TOKEN = os.environ["ONCALL_OSS_API_TOKEN"]

PRESERVE_EXISTING_USER_NOTIFICATION_RULES = (
    os.getenv("PRESERVE_EXISTING_USER_NOTIFICATION_RULES", "true").lower() == "true"
)
