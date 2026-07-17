import base64

from lib.jsm.config import JSM_API_BASE_URL, JSM_API_TOKEN, JSM_CLOUD_ID, JSM_EMAIL
from lib.network import api_call


class JsmAPIClient:
    DEFAULT_PAGE_SIZE = 100

    def __init__(
        self,
        api_base_url: str = JSM_API_BASE_URL,
        email: str = JSM_EMAIL,
        api_token: str = JSM_API_TOKEN,
    ):
        self.api_base_url = api_base_url
        credentials = base64.b64encode(f"{email}:{api_token}".encode()).decode()
        self.headers = {
            "Authorization": f"Basic {credentials}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _make_request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        json: dict | None = None,
        paginate: bool = True,
    ) -> dict:
        if params is None:
            params = {}

        if method.upper() != "GET" or not paginate:
            response = api_call(
                method,
                self.api_base_url,
                path,
                headers=self.headers,
                params=params,
                json=json,
            )
            return response.json()

        params.setdefault("size", self.DEFAULT_PAGE_SIZE)
        params.setdefault("offset", 0)
        combined_values: list[dict] = []

        while True:
            response = api_call(
                method,
                self.api_base_url,
                path,
                headers=self.headers,
                params=params,
            )
            data = response.json()
            values = data.get("values", [])
            combined_values.extend(values)

            if not data.get("links", {}).get("next") or not values:
                break
            params["offset"] = params["offset"] + len(values)

        return {"values": combined_values}

    def resolve_user_email(self, account_id: str) -> str | None:
        """Resolve Jira account ID to email via Jira REST API."""
        try:
            response = api_call(
                "GET",
                f"https://api.atlassian.com/ex/jira/{JSM_CLOUD_ID}/",
                "rest/api/3/user",
                headers=self.headers,
                params={"accountId": account_id},
            )
            return response.json().get("emailAddress")
        except Exception:
            return None

    def list_teams(self) -> list[dict]:
        response = self._make_request("GET", "teams")
        return response.get("values", [])

    def list_schedules(self) -> list[dict]:
        response = self._make_request(
            "GET", "schedules", params={"expand": "rotation"}
        )
        return response.get("values", [])

    def list_escalations_for_team(self, team_id: str) -> list[dict]:
        response = self._make_request(
            "GET", f"teams/{team_id}/escalations"
        )
        return response.get("values", [])

    def list_all_escalations(self) -> list[dict]:
        escalations = []
        teams = self.list_teams()
        for team in teams:
            for escalation in self.list_escalations_for_team(team["id"]):
                escalation["teamId"] = team["id"]
                escalation["teamName"] = team.get("name", team["id"])
                escalations.append(escalation)
        return escalations

    def list_integrations(self) -> list[dict]:
        response = self._make_request("GET", "integrations")
        return response.get("values", [])

    def list_notification_rules(self) -> list[dict]:
        response = self._make_request("GET", "notification-rules")
        return response.get("values", [])

    def list_users_from_resources(
        self,
        schedules: list[dict],
        escalations: list[dict],
        notification_rules: list[dict],
    ) -> list[dict]:
        """Build user list from resource references and notification rule contacts."""
        users_by_id: dict[str, dict] = {}

        def ensure_user(user_id: str, email: str | None = None) -> dict:
            if user_id not in users_by_id:
                users_by_id[user_id] = {
                    "id": user_id,
                    "email": email or "",
                    "username": email or user_id,
                    "fullName": email or user_id,
                    "notification_rules": [],
                }
            elif email and not users_by_id[user_id].get("email"):
                users_by_id[user_id]["email"] = email
                users_by_id[user_id]["username"] = email
                users_by_id[user_id]["fullName"] = email
            return users_by_id[user_id]

        for schedule in schedules:
            for rotation in schedule.get("rotations", []):
                for participant in rotation.get("participants", []):
                    if participant.get("type") == "user":
                        ensure_user(participant["id"])

        for escalation in escalations:
            for rule in escalation.get("rules", []):
                recipient = rule.get("recipient", {})
                if recipient.get("type") == "user":
                    ensure_user(recipient["id"])

        for user in users_by_id.values():
            if not user.get("email"):
                email = self.resolve_user_email(user["id"])
                if email:
                    user["email"] = email
                    user["username"] = email
                    user["fullName"] = email

        for rule in notification_rules:
            if rule.get("actionType") != "create-alert":
                continue
            steps = rule.get("steps", [])
            email = None
            for step in steps:
                contact = step.get("contact", {})
                if contact.get("to"):
                    email = contact["to"]
                    break
            if not email:
                continue
            matched = next(
                (u for u in users_by_id.values() if u.get("email") == email),
                None,
            )
            if matched:
                matched["notification_rules"].extend(steps)
            else:
                user = ensure_user(email, email=email)
                user["notification_rules"].extend(steps)

        return list(users_by_id.values())
