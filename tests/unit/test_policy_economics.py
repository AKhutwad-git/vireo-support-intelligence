import pytest
from vireo.policy.economics import (AGENT_STAFFING_COST_PER_HOUR_INR,
    calculate_replacement_cost, calculate_sla_breach_cost, calculate_transfer_cost, get_contact_cost)


@pytest.mark.parametrize("channel,cost", [("chat",210),("email",260),("voice",520),("social",240)])
def test_policy_channel_costs(channel, cost):
    assert get_contact_cost(channel) == cost


def test_sla_and_transfer_costs():
    assert calculate_sla_breach_cost(False) == 0
    assert calculate_sla_breach_cost(True) == 350
    assert [calculate_transfer_cost(n) for n in (0,1,2)] == [0,305,610]


def test_replacement_uses_only_unit_cost_plus_logistics():
    assert calculate_replacement_cost("1480") == 1820
    assert calculate_replacement_cost(None) is None


def test_staffing_rate_is_policy_context_not_elapsed_time_formula():
    assert AGENT_STAFFING_COST_PER_HOUR_INR == 165
    from vireo.analytics.economics import MONEY_FIELDS
    assert not any("labor" in field or "handle_time" in field for field in MONEY_FIELDS)
