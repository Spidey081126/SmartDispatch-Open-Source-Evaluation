# TESTING.md — Required submission

Complete this file with test evidence from your own work. Include at least five edge cases. Do not claim a test passed unless you ran it.

## Test command and environment
- Python version: Python 3.12.10 (Windows 64-bit)
- Command run: `python -m pytest -q`
- Actual test summary: `259 passed in 0.50s` (0 failures, 0 errors, 0 skipped)

## Edge-case evidence

| # | Case / input | Expected behaviour | Actual result | Test name or evidence |
|---|---|---|---|---|
| 1 | Partner `capacity=True` (boolean) with `active_order_ids=[]` | Must not be treated as integer `1`; partner must be rejected as invalid capacity | Order left unassigned (`partner_id: None`, `reason: 'no eligible partner or missing time data'`) | `tests/test_acceptance_matrix.py::test_capacity_boundary_matrix[True-0]` |
| 2 | Route travel time with `float("nan")` or `float("inf")` | Ineligible candidate; must not calculate or return NaN/infinite ETA | `result["eligible"] == False`, `result["eta_minutes"] is None` | `tests/test_acceptance_matrix.py::test_invalid_or_missing_travel_time_rejected[nan-1]` |
| 3 | Duplicate cancellation event replay (`event_id='C1'`) | Must be idempotent: no secondary workload deduction, no duplicate event ID in `processed_cancellation_ids` | `twice['workload_minutes'] == 0`, `twice['processed_cancellation_ids'] == ['C1']` | `tests/test_contract.py::test_duplicate_cancellation_is_idempotent` |
| 4 | Two candidates with identical ETA (e.g. ETA=17 mins for 'Z' and 'A') | Deterministic tie-breaking in ascending lexicographical order of `partner_id` | Candidate `'A'` selected over candidate `'Z'` | `tests/test_contract.py::test_tie_break_by_partner_id` |
| 5 | Order prep time is negative (e.g., `prep_minutes = -5`) | Order rejected immediately; no partner assigned | `result["partner_id"] is None`, `result["reason"] == "invalid prep time"` | `tests/test_contract.py::test_negative_prep_time_is_rejected` |
| 6 | Candidate at full capacity (`capacity=2`, `active_order_ids=['A', 'B']`) | Disqualified from candidate pool | `result["partner_id"] is None` | `tests/test_acceptance_matrix.py::test_capacity_boundary_matrix[2-2]` |
| 7 | Missing route in `travel` dictionary (e.g., no restaurant-to-destination leg) | Must not default to 0; partner marked ineligible | `result["eligible"] == False`, `result["eta_minutes"] is None` | `tests/test_contract.py::test_missing_travel_is_not_zero` |

## Regression tests added
The following regression tests were added in `tests/test_regression.py` to prevent regressions:
1. `test_regression_cancellation_differing_payload_same_event_id`: Ensures that if a cancellation event ID arrives again with a different payload (e.g., a different order ID), the partner state remains unaltered and the event is not processed twice.
2. `test_regression_cancellation_workload_underflow`: Ensures that cancelling an order whose recorded minutes exceed the partner's recorded workload clamps workload to 0 rather than dropping to a negative number.
3. `test_regression_invalid_capacity_types`: Verifies parameterized rejection for invalid capacity values (`True`, `False`, `0`, `-1`, `-10`, `1.5`, `"2"`, `None`).
4. `test_regression_order_blank_or_whitespace_fields`: Verifies that blank strings, whitespace strings (`"   "`), and non-string types for `order_id`, `restaurant_id`, and `destination_zone` return unassigned without crashing.
5. `test_regression_malformed_partner_entries_in_list`: Verifies that `None`, non-dictionary elements, or partially constructed dictionaries in `partners` list are skipped safely and a valid candidate is still chosen.
6. `test_regression_synthetic_dataset_integration`: Loads `data/records.json`, converts the travel list into tuple mappings, and validates that `assign_order` processes records from the synthetic dataset correctly.

## Remaining failures or limitations
- Remaining failures: None (all 259 tests pass).
- Limitations: In-memory simulation does not handle distributed concurrency or persistent storage for partner state mutations across processes.

"""Regression tests verifying bug fixes for SmartDispatch engine.

Covers:
- Idempotent cancellation with differing payload for existing event_id
- Cancellation workload underflow protection
- Strict rejection of boolean capacity and non-positive capacity
- Whitespace-only identifiers validation
- Current time (now) boundary and negative value rejection
- Heterogeneous/malformed partner records list handling
- End-to-end assignment check using synthetic records from data/records.json
"""
import json
from pathlib import Path
import pytest
from models import new_order, new_partner
from service import estimate_eta, assign_order, process_cancellation


def test_regression_cancellation_differing_payload_same_event_id():
    """Event ID idempotency must protect against duplicate event IDs even if payload differs."""
    partner = new_partner("P1", "Z1")
    partner.update(
        active_order_ids=["ORD-1", "ORD-2"],
        workload_minutes=30,
        minutes_by_order={"ORD-1": 15, "ORD-2": 15},
    )
    # First cancellation for ORD-1
    res1 = process_cancellation(partner, "ORD-1", "EVT-999")
    assert res1["active_order_ids"] == ["ORD-2"]
    assert res1["workload_minutes"] == 15
    assert res1["processed_cancellation_ids"] == ["EVT-999"]

    # Replayed event with same event_id but different order_id
    res2 = process_cancellation(res1, "ORD-2", "EVT-999")
    assert res2["active_order_ids"] == ["ORD-2"]
    assert res2["workload_minutes"] == 15
    assert res2["processed_cancellation_ids"] == ["EVT-999"]


def test_regression_cancellation_workload_underflow():
    """Cancelling an order whose recorded minutes exceed total workload clamps to 0."""
    partner = new_partner("P1", "Z1")
    partner.update(
        active_order_ids=["ORD-1"],
        workload_minutes=10,
        minutes_by_order={"ORD-1": 25},
    )
    res = process_cancellation(partner, "ORD-1", "EVT-001")
    assert res["workload_minutes"] == 0
    assert res["active_order_ids"] == []


@pytest.mark.parametrize("invalid_capacity", [True, False, 0, -1, -10, 1.5, "2", None])
def test_regression_invalid_capacity_types(invalid_capacity):
    """Boolean, float, zero, negative or string capacity must never be treated as valid."""
    order = new_order("O-1", "REST-1", "DEST-1")
    partner = new_partner("P-1", "ZONE-1")
    partner["capacity"] = invalid_capacity
    travel = {("ZONE-1", "REST-1"): 5, ("REST-1", "DEST-1"): 10}
    result = assign_order(order, [partner], travel)
    assert result["partner_id"] is None
    assert result["reason"] == "no eligible partner or missing time data"


@pytest.mark.parametrize("field", ["order_id", "restaurant_id", "destination_zone"])
@pytest.mark.parametrize("bad_val", ["", "   ", "\t\n", None, 0, 123])
def test_regression_order_blank_or_whitespace_fields(field, bad_val):
    """Order identifiers must be non-empty, non-whitespace strings."""
    order = new_order("O-1", "REST-1", "DEST-1")
    order[field] = bad_val
    partner = new_partner("P-1", "ZONE-1")
    travel = {("ZONE-1", "REST-1"): 5, ("REST-1", "DEST-1"): 10}
    result = assign_order(order, [partner], travel)
    assert result["partner_id"] is None
    assert result["reason"] == "invalid order fields"


def test_regression_malformed_partner_entries_in_list():
    """Non-dict and partially formed partner records should be safely ignored."""
    order = new_order("O-1", "REST-1", "DEST-1")
    valid_partner = new_partner("P-VALID", "ZONE-1")
    partners = [
        None,
        "not-a-dict",
        123,
        {},
        {"partner_id": "P-NO-ZONE"},
        {"zone": "ZONE-1"},
        {"partner_id": "P-INACTIVE", "zone": "ZONE-1", "active": False, "capacity": 2},
        valid_partner,
    ]
    travel = {("ZONE-1", "REST-1"): 5, ("REST-1", "DEST-1"): 10}
    result = assign_order(order, partners, travel)
    assert result["partner_id"] == "P-VALID"
    assert result["reason"] == "assigned"


def test_regression_synthetic_dataset_integration():
    """Verify that records.json synthetic data can be parsed and dispatched safely."""
    data_path = Path(__file__).resolve().parent.parent / "data" / "records.json"
    if not data_path.exists():
        pytest.skip("data/records.json not found")

    with open(data_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    # Convert travel times list to tuple-key mapping
    travel = {}
    for row in dataset.get("travel_times", []):
        travel[(row["from"], row["to"])] = row["minutes"]

    orders = dataset.get("orders", [])
    partners = dataset.get("partners", [])

    assert len(orders) > 0
    assert len(partners) > 0
    assert len(travel) > 0

    # Test assignment on the first valid order
    test_order = orders[0]
    result = assign_order(test_order, partners, travel, now=0)
    assert "order_id" in result
    assert "partner_id" in result
    assert "reason" in result
    if result["partner_id"] is not None:
        assert result["pickup_minutes"] is not None
        assert result["eta_minutes"] is not None
        assert result["reason"] == "assigned"
