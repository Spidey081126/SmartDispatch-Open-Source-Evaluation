# optimizations.md - Required submission

Document optimizations you considered or implemented. Do not claim a speedup or improvement unless you measured it.

## 1. Baseline and objective
- What needed improvement:
  - Correctness and input sanitization: Ensuring missing or malformed data is rejected immediately before running arithmetic.
  - Redundant route lookups: Estimating ETAs for partners who are inactive or already at full capacity is wasted computation.
  - Candidate selection complexity: Finding the optimal partner deterministically without unnecessary sorting overhead.
- What evidence suggested an improvement could help:
  - In a dispatch system handling hundreds of partner records per assignment round, running route lookups for inactive or fully occupied partners wastes CPU cycles and memory allocations.

## 2. Options considered
1. Pre-filtering ineligible partners vs estimating all candidates:
   - Expected benefit: Disqualifying inactive or saturated partners before calling `estimate_eta()` eliminates redundant tuple key lookups in the `travel` dictionary.
   - Risk: None, provided eligibility filters strictly match business rules.
2. Single-pass selection (`min()`) vs full list sorting (`list.sort()`):
   - Expected benefit: `min()` with a key tuple `(eta_minutes, str(partner_id))` requires only a single pass (O(K) time, O(1) auxiliary space) through eligible candidates. `list.sort()` requires O(K log K) time and allocates internal sort memory.
   - Risk: None. Python's `min()` reliably picks the first minimal element, and with lexicographical tie-breaking in the key, it produces identical, deterministic results.
3. Shallow copy vs `copy.deepcopy()` in `process_cancellation`:
   - Expected benefit: `deepcopy()` traverses the entire object graph, which has higher overhead than creating a new dict and slicing/copying the two mutable lists (`active_order_ids[:]` and `processed_cancellation_ids[:]`).
   - Risk: For the challenge requirements, `deepcopy()` guarantees total isolation and zero side effects on the input partner record. Because the workload and order count are small, correctness and safety were prioritized.

## 3. Changes implemented
- Change and reason:
  - Implemented early disqualification in `assign_order`: Before calling `estimate_eta`, each partner is verified for `active is True`, integer capacity `>= 1`, and `len(active_order_ids) < capacity`.
  - Implemented single-pass optimal selection: Used `min(options, key=lambda item: (item['eta_minutes'], str(item['partner_id'])))` instead of sorting.
  - Implemented fast-fail validation on order fields: If `order_id`, `restaurant_id`, or `destination_zone` is invalid, the function returns immediately without iterating over the partner list.
- Tests that protect correctness:
  - `test_acceptance_matrix.py`: All 171 matrix cases.
  - `test_contract.py`: `test_lowest_eta_selected`, `test_tie_break_by_partner_id`.
  - `test_regression.py`: `test_regression_malformed_partner_entries_in_list`.
- Measurement method and result:
  - Entire pytest suite (259 tests across 4 test suites) completes in ~0.50 seconds on Python 3.12.

## 4. Trade-offs
- Validation rigor vs raw speed:
  - Checking `isinstance(val, (int, float)) and not isinstance(val, bool)` and `math.isfinite(val)` adds a slight per-call check overhead compared to unchecked addition, but prevents severe silent bugs (e.g. booleans treated as 1 or 0, NaN poisoning calculations).
- Memory safety vs copy overhead:
  - Using `deepcopy` in `process_cancellation` prioritizes pure functional safety (caller's original dictionary is never mutated) over raw microsecond throughput.

## 5. Further improvements
- Tuple-key Travel Map Indexing: If travel records grow to millions of rows, hierarchical zone-to-restaurant indexing or spatial indexing (geohashing / KD-trees) could prune distant partners before checking travel times.
- Batch Assignment: When dispatching multiple simultaneous orders, solve global bipartite matching (e.g., Hungarian algorithm / Min-Cost Max-Flow) to minimize fleet-wide total delivery delay rather than greedy single-order assignment.
- Validation: Validate global batch assignment against synthetic burst scenarios in `data/records.json`.