import requests

from lib.base_config import MIGRATING_FROM, ONCALL_API_TOKEN, ONCALL_API_URL
from lib.network import api_call as _api_call
from lib.session import get_or_create_session_id


def _delegate_to_default_or_instance(method_name: str):
    """Descriptor: on class use default instance; on instance use self."""
    class Descriptor:
        def __get__(self, obj, owner):
            if obj is None:
                return lambda *args, **kwargs: getattr(owner._get_default(), method_name)(*args, **kwargs)
            return lambda *args, **kwargs: getattr(obj, f"_{method_name}")(*args, **kwargs)
    return Descriptor()


class OnCallAPIClient:
    """Client for the Grafana OnCall API. Can be used as default (target) or instantiated with custom URL/token (e.g. source OSS)."""

    _default_instance = None

    def __init__(
        self,
        api_url: str | None = None,
        api_token: str | None = None,
        user_agent_suffix: str | None = None,
    ):
        self._api_url = (api_url or ONCALL_API_URL).rstrip("/") + "/"
        self._api_token = api_token or ONCALL_API_TOKEN
        self._user_agent_suffix = user_agent_suffix or MIGRATING_FROM
        self._session_id = get_or_create_session_id()

    def _api_call(self, method: str, path: str, **kwargs) -> requests.Response:
        kwargs.setdefault("headers", {})
        kwargs["headers"].update(
            {
                "Authorization": self._api_token,
                "User-Agent": f"IRM Migrator - {self._user_agent_suffix} - {self._session_id}",
            }
        )
        return _api_call(method, self._api_url, path, **kwargs)

    def _list_all(self, path: str) -> list[dict]:
        response = self._api_call("get", path)
        data = response.json()
        results = list(data.get("results", []))

        while data.get("next"):
            next_path = data["next"]
            response = self._api_call("get", next_path)
            data = response.json()
            results.extend(data.get("results", []))

        return results

    list_all = _delegate_to_default_or_instance("list_all")

    def _create(self, path: str, payload: dict) -> dict:
        response = self._api_call("post", path, json=payload)
        return response.json()

    create = _delegate_to_default_or_instance("create")

    def _delete(self, path: str) -> None:
        try:
            self._api_call("delete", path)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code != 404:
                raise

    delete = _delegate_to_default_or_instance("delete")

    def _update(self, path: str, payload: dict) -> dict:
        response = self._api_call("put", path, json=payload)
        return response.json()

    update = _delegate_to_default_or_instance("update")

    def _list_users_with_notification_rules(self) -> list[dict]:
        users = self._list_all("users")
        rules = self._list_all("personal_notification_rules")
        rules_by_user: dict[str, list[dict]] = {}
        for r in rules:
            uid = r.get("user_id")
            if uid is not None:
                rules_by_user.setdefault(uid, []).append(r)
        for user in users:
            user["notification_rules"] = rules_by_user.get(user["id"], [])
        return users

    list_users_with_notification_rules = _delegate_to_default_or_instance("list_users_with_notification_rules")

    def list_escalation_chains(self) -> list[dict]:
        return self._list_all("escalation_chains")

    def list_escalation_policies(self, escalation_chain_id: str | None = None) -> list[dict]:
        if escalation_chain_id:
            return self._list_all(f"escalation_policies/?escalation_chain_id={escalation_chain_id}")
        return self._list_all("escalation_policies")

    def list_schedules(self) -> list[dict]:
        return self._list_all("schedules")

    def list_on_call_shifts(self, schedule_id: str | None = None) -> list[dict]:
        if schedule_id:
            return self._list_all(f"on_call_shifts/?schedule_id={schedule_id}")
        return self._list_all("on_call_shifts")

    def list_integrations(self) -> list[dict]:
        return self._list_all("integrations")

    def list_routes(self, integration_id: str | None = None) -> list[dict]:
        if integration_id is not None:
            return self._list_all(f"routes/?integration_id={integration_id}")
        return self._list_all("routes")

    @classmethod
    def _get_default(cls) -> "OnCallAPIClient":
        if cls._default_instance is None:
            cls._default_instance = cls()
        return cls._default_instance

    @classmethod
    def api_call(cls, method: str, path: str, **kwargs) -> requests.Response:
        return cls._get_default()._api_call(method, path, **kwargs)
