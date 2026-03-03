"""
Instance-based API client for reading from a Grafana OnCall OSS instance.
Uses the same OnCall API v1 format as the target IRM instance.
"""

import requests

from lib.network import api_call as _api_call
from lib.session import get_or_create_session_id


class OnCallSourceClient:
    """Read-only client for a source OnCall OSS instance."""

    def __init__(self, api_url: str, api_token: str):
        self.api_url = api_url.rstrip("/") + "/"
        self.api_token = api_token
        self._session_id = get_or_create_session_id()

    def _api_call(self, method: str, path: str, **kwargs) -> requests.Response:
        kwargs.setdefault("headers", {})
        kwargs["headers"].update(
            {
                "Authorization": self.api_token,
                "User-Agent": f"IRM Migrator - oncall_oss - {self._session_id}",
            }
        )
        return _api_call(method, self.api_url, path, **kwargs)

    def list_all(self, path: str) -> list[dict]:
        """List all paginated results for the given path (e.g. 'schedules', 'integrations')."""
        response = self._api_call("get", path)
        data = response.json()
        results = list(data.get("results", []))

        while data.get("next"):
            next_path = data["next"]
            response = self._api_call("get", next_path)
            data = response.json()
            results.extend(data.get("results", []))

        return results

    def list_escalation_chains(self) -> list[dict]:
        return self.list_all("escalation_chains")

    def list_escalation_policies(self, escalation_chain_id: str | None = None) -> list[dict]:
        if escalation_chain_id:
            return self.list_all(f"escalation_policies/?escalation_chain_id={escalation_chain_id}")
        return self.list_all("escalation_policies")

    def list_schedules(self) -> list[dict]:
        return self.list_all("schedules")

    def list_on_call_shifts(self, schedule_id: str | None = None) -> list[dict]:
        if schedule_id:
            return self.list_all(f"on_call_shifts/?schedule_id={schedule_id}")
        return self.list_all("on_call_shifts")

    def list_integrations(self) -> list[dict]:
        return self.list_all("integrations")

    def list_routes(self, integration_id: str) -> list[dict]:
        return self.list_all(f"routes/?integration_id={integration_id}")

    def list_users(self) -> list[dict]:
        return self.list_all("users")

    def list_personal_notification_rules(self) -> list[dict]:
        return self.list_all("personal_notification_rules")

    def list_users_with_notification_rules(self) -> list[dict]:
        """Return users with their personal_notification_rules attached."""
        users = self.list_users()
        rules = self.list_personal_notification_rules()
        for user in users:
            user["notification_rules"] = [
                r for r in rules if r.get("user_id") == user["id"]
            ]
        return users
