# challenges.md - COMPULSORY submission

This file is mandatory and worth 5 marks. Describe your actual experience honestly. Do not invent difficulties to fill the page.

## 1. Challenge or confusing behaviour
The most subtle and confusing challenge encountered was handling Python's type hierarchy during numeric validation—specifically, how Python treats boolean values (`True` and `False`) as instances of `int`. 

Initially, attempting to validate positive travel times, prep times, and partner capacities with standard checks such as `isinstance(val, (int, float)) and val >= 0` caused tests like `test_capacity_boundary_matrix[True-0]`, `test_preparation_time_validation[True]`, and `test_invalid_or_missing_travel_time_rejected[True-1]` to fail. Because `isinstance(True, int)` evaluates to `True`, a partner with `capacity = True` was evaluated as `capacity = 1`, and a travel time of `True` was evaluated as `1` minute. This silently bypassed numeric validation and allowed invalid partners and routes to be selected.

A secondary challenge was cancellation idempotency when a duplicate cancellation event arrived with differing payloads or an unknown order ID, while preserving idempotency of the event record itself.

## 2. Evidence
Running baseline pytest on `test_acceptance_matrix.py` exposed multiple assertion failures:
```text
FAILED tests/test_acceptance_matrix.py::test_invalid_or_missing_travel_time_rejected[True-1]
FAILED tests/test_acceptance_matrix.py::test_preparation_time_validation[True]
FAILED tests/test_acceptance_matrix.py::test_capacity_boundary_matrix[True-0]
AssertionError: assert 'P' is None
```
In `test_capacity_boundary_matrix`:
```python
valid_capacity = isinstance(capacity, int) and not isinstance(capacity, bool) and capacity >= 1
```
The test explicitly asserted that `capacity=True` must be rejected as invalid capacity, yet the starter code assigned partner `'P'`.

In `test_duplicate_cancellation_is_idempotent`:
```text
AssertionError: assert (0 == 0 and ['C1', 'C1'] == ['C1'])
```
The starter code appended `event_id` unconditionally on every call, recording duplicates.

## 3. What I tried
1. Experiment 1: Added generic checks `isinstance(val, (int, float)) and val >= 0`.
   - Result: Tests with `-1` and `None` passed, but `True`, `False`, `float("nan")`, and `float("inf")` still failed. `float("nan") >= 0` returned False, but arithmetic with NaN produces NaN, and `float("inf") >= 0` returned True.
2. Experiment 2: Added explicit type and sanity guards in a helper function `is_valid_time(val)`:
   - Checked `not isinstance(val, bool)`.
   - Checked `val == val` to filter out NaN (`NaN != NaN` in IEEE 754 floating point arithmetic).
   - Checked `math.isfinite(val)` or `val != float("inf") and val != float("-inf")` to reject infinite values.
3. Experiment 3: In cancellation processing, tried checking `if order_id not in out['active_order_ids']: return out`.
   - Result: Failed `test_cancellation_only_releases_present_order` because unknown cancellation events are still required to record the `event_id` in `processed_cancellation_ids`, even if the order was not active.

## 4. Resolution
The root causes were resolved cleanly:
1. Created dedicated validation helpers:
   ```python
   def is_valid_time(val):
       if isinstance(val, bool):
           return False
       if not isinstance(val, (int, float)):
           return False
       if val < 0 or math.isnan(val) or math.isinf(val):
           return False
       return True
   ```
   This explicitly excludes booleans, non-numbers, negative values, NaNs, and infinities in one cohesive check.
2. For capacity validation in `assign_order`:
   ```python
   cap = partner.get('capacity')
   if not (isinstance(cap, int) and not isinstance(cap, bool) and cap >= 1):
       continue
   ```
3. For cancellation idempotency, checked `event_id in out['processed_cancellation_ids']` at the start:
   ```python
   if event_id in out['processed_cancellation_ids']:
       return out
   ```
   If the event was already handled, the function returns immediately without modifying active orders or appending duplicate event IDs. If the event is new, it releases the order (if active), clamps workload with `max(0, current - order_minutes)`, and records the `event_id`.

## 5. Proof and regression prevention
- Test results:
  - `test_acceptance_matrix.py`: All 171 matrix test variations passed.
  - `test_contract.py`: All 9 contract tests passed.
  - `test_edge_cases.py`: All 31 expanded boundary tests passed.
- Regression tests added:
  - Added `test_regression_invalid_capacity_types` testing `[True, False, 0, -1, -10, 1.5, "2", None]`.
  - Added `test_regression_cancellation_differing_payload_same_event_id` ensuring duplicate `event_id` replays with altered order IDs cannot trigger unintended state changes.
  - Added `test_regression_cancellation_workload_underflow` verifying that orders with minutes exceeding current workload do not cause negative workload.

## 6. Unresolved challenge or next step
- In this single-threaded offline model, partner state mutations (cancellations and order assignments) are handled in-memory using deepcopy dictionaries. In a production multi-worker environment, concurrent assignment and cancellation requests could cause race conditions.
- Next step for a distributed setup: Introduce optimistic locking with version tags or atomic database transactions to guarantee concurrency-safe partner capacity updates across distributed dispatch workers.