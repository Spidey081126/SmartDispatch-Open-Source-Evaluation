# approach.md - Required submission

Complete this file in your own words. Be concise and specific to the work you actually performed.

## 1. Baseline
- Commands run before editing:
  - `python -m pip install -r requirements-dev.txt`
  - `python -m pytest -q`
  - `python -m main`
- Initial test result (include the actual summary):
  - Baseline execution produced: `65 failed, 164 passed in 1.66s` (229 total tests).
  - 4 failures in `tests/test_contract.py` (`test_inactive_partner_not_assigned`, `test_full_partner_not_assigned`, `test_negative_prep_time_is_rejected`, `test_duplicate_cancellation_is_idempotent`).
  - 61 failures in `tests/test_acceptance_matrix.py` across invalid travel time formats, negative/NaN/infinite prep times, inactive partner assignments, capacity boundary violations, duplicate cancellation idempotency, and invalid order fields.
- Demo/output observed:
  - `python -m main` printed: `{'order_id': 'O-7', 'partner_id': 'P-2', 'pickup_minutes': 13, 'eta_minutes': 35, 'reason': 'assigned'}`.

## 2. Codebase understanding
- Important files/functions inspected:
  - `service.py`: Contains the core dispatch engine logic: `estimate_eta`, `assign_order`, and `process_cancellation`.
  - `models.py`: Helper constructors `new_partner` and `new_order` defining dictionary structures and initial defaults.
  - `fixtures.py` & `main.py`: Provides static sample data and the demo entry point.
  - `tests/test_contract.py`, `tests/test_acceptance_matrix.py`, `tests/test_edge_cases.py`: Acceptance matrices and contract specifications.
  - `data/records.json`: Expanded synthetic dataset with 180 orders, 60 partners, 387 travel time records, and 177 cancellation events.
- Candidate filtering, ETA calculation, and capacity flow traced:
  - In `assign_order`: Validates order fields (`order_id`, `restaurant_id`, `destination_zone`, `prep_minutes`) and `now`. Iterates through partners to check active status (`active is True`), capacity validity (`isinstance(capacity, int)` and `capacity >= 1`), and active order load (`len(active_order_ids) < capacity`).
  - In `estimate_eta`: Fetches routes `(partner.zone, restaurant_id)` and `(restaurant_id, destination_zone)`. Validates that travel times, `prep_minutes`, `workload_minutes`, and `now` are non-negative, finite numbers (rejecting booleans, strings, NaN, inf).
  - Formulas:
    - Pickup time: `pickup_minutes = now + leg1 + workload_minutes`
    - Delivery ETA: `eta_minutes = pickup_minutes + prep_minutes + leg2`
  - Partner selection: Selects eligible partner minimizing `(eta_minutes, str(partner_id))` for deterministic tie-breaking.
  - In `process_cancellation`: Guards against duplicate `event_id`, safely removes `order_id` from `active_order_ids`, reduces `workload_minutes` clamped at 0, and records `event_id`.
- How you confirmed your understanding:
  - Verified logic by tracing parameter sets in `test_acceptance_matrix.py` and comparing against the requirements in `STUDENT_PROBLEM_STATEMENT.md`.

## 3. Investigation and implementation strategy
For each major defect, describe the symptom, hypothesis, evidence from a test/log/example, and the fix chosen.
- Issue 1: Inactive and At-Capacity Partners Assigned
  - Symptom: `test_inactive_partner_not_assigned` and `test_full_partner_not_assigned` failed with `AssertionError: assert 'P' is None`.
  - Hypothesis: Starter `assign_order` looped over `partners` without checking `active` flag or `len(active_order_ids) >= capacity`.
  - Evidence: In `service.py`, starter code had a comment: `# Starter is intentionally incomplete: active/capacity/time validation is missing`.
  - Fix: Checked `partner.get('active') is True`, validated `capacity` as positive integer (excluding `bool`), and required `len(partner.get('active_order_ids', [])) < capacity`.
- Issue 2: Invalid/Non-Numeric/Negative Time Inputs Accepted
  - Symptom: 61 parameterized test failures in `test_acceptance_matrix.py` when passing `-1`, `None`, `"2"`, `True`, `float("nan")`, or `float("inf")`.
  - Hypothesis: Starter code performed direct addition (`now + leg1 + workload`) without type checking or range validation. In Python, `isinstance(True, int)` is True, so booleans were mistakenly treated as numbers (1 or 0).
  - Evidence: Test failures in `test_invalid_or_missing_travel_time_rejected` and `test_preparation_time_validation`.
  - Fix: Implemented `is_valid_time(val)` requiring `isinstance(val, (int, float)) and not isinstance(val, bool) and val >= 0 and math.isfinite(val)`. Applied this to `now`, `prep_minutes`, `workload_minutes`, `leg1`, and `leg2`.
- Issue 3: Duplicate Cancellation Events Applied Multiple Times
  - Symptom: `test_duplicate_cancellation_is_idempotent` failed with `['C1', 'C1'] == ['C1']`.
  - Hypothesis: `process_cancellation` appended `event_id` to `processed_cancellation_ids` without checking if `event_id` was already present.
  - Evidence: Calling `process_cancellation` twice with the same `event_id` repeatedly decremented workload and appended duplicate event IDs.
  - Fix: Added an idempotency guard: `if event_id in out['processed_cancellation_ids']: return out`. Also ensured workload never drops below 0 via `max(0, ...)`.
- Issue 4: Malformed and Missing Order Identifier Fields
  - Symptom: `test_invalid_order_fields_do_not_assign_partner` failed when `order_id`, `restaurant_id`, or `destination_zone` was `""`, `None`, or `0`.
  - Hypothesis: Starter code did not check whether identifier fields were non-empty strings.
  - Fix: Implemented `is_valid_id(val)` requiring non-empty string and returned an unassigned result when invalid.

## 4. Implementation decisions
- Main changes and why:
  - Extracted helper functions `is_valid_time(val)` and `is_valid_id(val)` to ensure uniform, rigorous validation across `estimate_eta` and `assign_order`.
  - Handled candidate selection with `min(options, key=lambda item: (item['eta_minutes'], str(item['partner_id'])))` for strict O(N) evaluation and deterministic ascending lexicographical tie-breaking.
  - Made `process_cancellation` strictly idempotent by checking `event_id in processed_cancellation_ids` before any mutations.
- Alternatives considered and why rejected:
  - Alternative: Sorting candidate list beforehand. Rejected because `min()` with a key tuple is O(N) time and O(1) auxiliary space, whereas `sort()` is O(N log N).
  - Alternative: Using `try...except TypeError` for time arithmetic. Rejected because Python treats `True` as `1` and `False` as `0`, which would silently allow booleans as valid minutes without raising `TypeError`.
- Assumptions:
  - Unassigned orders return a dictionary containing `'partner_id': None`, `'eta_minutes': None`, and an informative `'reason'`.
  - Cancellation events are identified uniquely by `event_id`. Duplicate event deliveries must not alter partner state.

## 5. Verification
- Tests added or changed:
  - Created `tests/test_regression.py` containing 30 new tests covering:
    - Cancellation idempotency when payload differs for the same `event_id`.
    - Cancellation workload underflow clamping.
    - Rejection of invalid capacity types (booleans, zero, negatives, floats, strings).
    - Rejection of whitespace-only or non-string order identifiers.
    - Handling of heterogeneous / malformed partner records in candidate lists.
    - Integration test parsing `data/records.json` travel times into tuple mappings.
- Commands run and actual results:
  - `python -m pytest -q` -> `259 passed in 0.50s`.
  - `python -m main` -> `{'order_id': 'O-7', 'partner_id': 'P-2', 'pickup_minutes': 13, 'eta_minutes': 35, 'reason': 'assigned'}`.
- Edge cases verified:
  - Zero-duration travel, prep, and workload boundary values.
  - Missing travel routes resulting in explicit ineligibility without defaulting to zero.
  - Lexicographic partner ID tie-breaking on identical ETAs.
  - Inactive partner exclusion and capacity saturation.
  - Duplicate cancellation suppression.
- Remaining failures or known limitations:
  - 0 remaining failures across all 259 tests.