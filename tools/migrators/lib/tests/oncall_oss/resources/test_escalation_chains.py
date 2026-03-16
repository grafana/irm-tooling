from unittest.mock import patch

from lib.oncall_oss.resources.escalation_chains import (
    _remap_policy_step,
    match_escalation_chain,
    migrate_escalation_chain,
)


def test_match_escalation_chain():
    chain = {"id": "c1", "name": "Critical"}
    oncall_chains = [
        {"id": "oc1", "name": "Critical"},
        {"id": "oc2", "name": "Other"},
    ]
    match_escalation_chain(chain, oncall_chains)
    assert chain["oncall_escalation_chain"]["id"] == "oc1"


def test_match_escalation_chain_case_insensitive():
    chain = {"id": "c1", "name": "Critical Alerts"}
    oncall_chains = [{"id": "oc1", "name": "critical alerts"}]
    match_escalation_chain(chain, oncall_chains)
    assert chain["oncall_escalation_chain"] is not None


def test_match_escalation_chain_no_match():
    chain = {"id": "c1", "name": "New Chain"}
    oncall_chains = [{"id": "oc1", "name": "Other"}]
    match_escalation_chain(chain, oncall_chains)
    assert chain["oncall_escalation_chain"] is None


def test_remap_policy_step_wait():
    step = {"type": "wait", "position": 0, "duration": 300}
    payload = _remap_policy_step(step, "new_chain_id", {}, {})
    assert payload["escalation_chain_id"] == "new_chain_id"
    assert payload["type"] == "wait"
    assert payload["duration"] == 300


def test_remap_policy_step_notify_persons():
    step = {
        "type": "notify_persons",
        "position": 1,
        "persons_to_notify": ["u1", "u2"],
    }
    payload = _remap_policy_step(
        step, "new_chain_id", {"u1": "ou1", "u2": "ou2"}, {}
    )
    assert payload["persons_to_notify"] == ["ou1", "ou2"]


def test_remap_policy_step_notify_persons_skips_unmapped():
    step = {"type": "notify_persons", "persons_to_notify": ["u1"]}
    payload = _remap_policy_step(step, "new_chain_id", {}, {})
    assert payload is None


def test_remap_policy_step_notify_on_call_from_schedule():
    step = {
        "type": "notify_on_call_from_schedule",
        "notify_on_call_from_schedule": "s1",
    }
    payload = _remap_policy_step(step, "new_chain_id", {}, {"s1": "os1"})
    assert payload["notify_on_call_from_schedule"] == "os1"


def test_remap_policy_step_notify_on_call_from_schedule_unmapped_returns_none():
    step = {
        "type": "notify_on_call_from_schedule",
        "notify_on_call_from_schedule": "s1",
    }
    payload = _remap_policy_step(step, "new_chain_id", {}, {})
    assert payload is None


@patch("lib.oncall_oss.resources.escalation_chains.OnCallAPIClient")
def test_migrate_escalation_chain(mock_client):
    mock_client.create.side_effect = [
        {"id": "new_chain_id"},
        {"id": "ep1"},
        {"id": "ep2"},
    ]
    chain = {"id": "c1", "name": "Test Chain", "oncall_escalation_chain": None}
    policies = [
        {"type": "wait", "position": 0, "duration": 60},
        {"type": "notify_persons", "position": 1, "persons_to_notify": ["u1"]},
    ]
    user_id_map = {"u1": "ou1"}
    schedule_id_map = {}

    result = migrate_escalation_chain(chain, policies, user_id_map, schedule_id_map)

    assert result["id"] == "new_chain_id"
    mock_client.create.assert_any_call(
        "escalation_chains",
        {"name": "Test Chain", "team_id": None},
    )
    assert mock_client.create.call_count == 3
