# DISPATCH_NOTES.md — Required submission

Complete this file with your own actual examples and results. Do not leave prompts unanswered.

## 1. Worked ETA example
### Inputs:
- Current simulation time (`now`): `0` minutes
- Order:
  - `order_id`: `"O-7"`
  - `restaurant_id`: `"R-2"`
  - `destination_zone`: `"Z-9"`
  - `prep_minutes`: `10`
- Candidate Partner:
  - `partner_id`: `"P-2"`
  - `zone`: `"Z-1"`
  - `active`: `True`
  - `capacity`: `2`
  - `active_order_ids`: `["OLD-1"]` (1 active order < capacity of 2; eligible)
  - `workload_minutes`: `5`
- Travel Times Map:
  - Partner-to-restaurant: `("Z-1", "R-2")` = `8` minutes (`leg1`)
  - Restaurant-to-customer: `("R-2", "Z-9")` = `12` minutes (`leg2`)

### Step-by-Step Calculation:
1. **Pickup Time Calculation**:
   $$\text{pickup\_minutes} = \text{now} + \text{leg1} + \text{workload\_minutes}$$
   $$\text{pickup\_minutes} = 0 + 8 + 5 = 13\text{ minutes}$$
2. **Delivery ETA Calculation**:
   $$\text{eta\_minutes} = \text{pickup\_minutes} + \text{prep\_minutes} + \text{leg2}$$
   $$\text{eta\_minutes} = 13 + 10 + 12 = 35\text{ minutes}$$

### Actual Observed Result:
Running `assign_order(order, [p1, p2], travel)` returns:
```python
{
    'order_id': 'O-7',
    'partner_id': 'P-2',
    'pickup_minutes': 13,
    'eta_minutes': 35,
    'reason': 'assigned'
}
```

## 2. No-eligible-partner example
### Scenario:
An order is submitted for delivery from restaurant `"R-10"` to destination `"Z-50"`. Two partners exist in the fleet:
- Partner `"P-FULL"`:
  - `zone`: `"Z-1"`
  - `active`: `True`
  - `capacity`: `1`
  - `active_order_ids`: `["ORD-PREV"]`
  - **Ineligibility reason**: Partner is at maximum capacity (`len(active_order_ids) == capacity`). Disqualified during candidate filtering.
- Partner `"P-NOROUTE"`:
  - `zone`: `"Z-2"`
  - `active`: `True`
  - `capacity`: `2`
  - `active_order_ids`: `[]`
  - Travel map only contains: `{("Z-2", "R-10"): 6}`. Missing route `("R-10", "Z-50")`.
  - **Ineligibility reason**: Required leg 2 travel time is missing from the travel matrix. In accordance with rule 5, missing travel times must never be assumed to be 0.
- Order Dispatch Execution:
  - Neither partner qualifies as an eligible option.
  - Actual return:
    ```python
    {
        'order_id': 'ORD-99',
        'partner_id': None,
        'eta_minutes': None,
        'reason': 'no eligible partner or missing time data'
    }
    ```

## 3. Three edge cases
### Case 1: Inactive Partner Exclusion
- **Input**:
  - `order = new_order("ORD-1", "R-1", "D-1", 10)`
  - `partner = new_partner("P-INACTIVE", "Z-1")` with `partner["active"] = False`
  - `travel = {("Z-1", "R-1"): 5, ("R-1", "D-1"): 10}`
- **Expected Behaviour**: Inactive partner must never be assigned regardless of proximity.
- **Actual Result**: `{'order_id': 'ORD-1', 'partner_id': None, 'eta_minutes': None, 'reason': 'no eligible partner or missing time data'}`
- **Verifying Test**: `tests/test_contract.py::test_inactive_partner_not_assigned`

### Case 2: Lexicographic Tie-Breaking with Identical ETAs
- **Input**:
  - Two partners: `"Z-PARTNER"` (zone `"Z1"`) and `"A-PARTNER"` (zone `"Z2"`)
  - Travel times: `("Z1", "R")`: 5 mins, `("Z2", "R")`: 5 mins, `("R", "D")`: 10 mins
  - Both candidates produce identical pickup time of 5 mins and identical ETA of 25 mins.
- **Expected Behaviour**: Ascending lexicographical comparison on `partner_id` selects `"A-PARTNER"` over `"Z-PARTNER"`.
- **Actual Result**: `result["partner_id"] == "A-PARTNER"`
- **Verifying Test**: `tests/test_contract.py::test_tie_break_by_partner_id`

### Case 3: Duplicate Cancellation Idempotency
- **Input**:
  - `partner` with `active_order_ids = ["ORD-A"]`, `workload_minutes = 20`, and `minutes_by_order = {"ORD-A": 20}`
  - Cancellation event `"EVT-100"` for `"ORD-A"` received and processed once.
  - The same cancellation event `"EVT-100"` for `"ORD-A"` is submitted a second time.
- **Expected Behaviour**: Second call must detect existing `EVT-100` in `processed_cancellation_ids` and return immediately without double-decrementing workload or duplicating event records.
- **Actual Result**: `result["workload_minutes"] == 0`, `result["processed_cancellation_ids"] == ["EVT-100"]`, and `result["active_order_ids"] == []`.
- **Verifying Test**: `tests/test_contract.py::test_duplicate_cancellation_is_idempotent`

## 4. Assumptions and limitations
- **Tie-Breaking**: When multiple partners share the exact same minimum ETA, ties are resolved deterministically using Python's standard string comparison (`str(partner_id)` in ascending order).
- **Workload Accounting**: Workload represents minutes remaining on already-assigned active deliveries. When an active order is cancelled, only the minutes associated with that specific order (looked up from `minutes_by_order`) are deducted. Workload is clamped at zero using `max(0, ...)` to protect against negative underflow.
- **Cancellation Idempotency**: Cancellation deduplication is keyed on `event_id`. An event ID recorded in `processed_cancellation_ids` will not be processed again even if replayed with a differing payload.
- **Data Integrity Assumptions**: Travel times and preparation minutes are expected to be finite, non-negative numbers (`int` or `float`). Boolean values (`True`/`False`), strings, `NaN`, and `inf` are treated as invalid data, making candidates ineligible.
- **System Limitations**: Dispatching operates on single-order evaluation in-memory. Multi-order batch optimization and atomic persistence for distributed workers are outside the scope of this engine.
