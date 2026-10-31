# Student start here — ShuttleOps

This file is the reading checklist for this evaluation. Read the linked documents before editing code. You are responsible for understanding the starter code, data, tests and required submission files.

## 1. Read the problem statement first

- [Open the student problem statement PDF](docs/Problem_Statement.pdf)
- [Open the Markdown problem statement](STUDENT_PROBLEM_STATEMENT.md)

The Markdown file is the source of truth if a later change makes the PDF differ. Re-read the brief before final submission.

## 2. Read the workflow and integrity rules

- [README and setup instructions](README.md)
- [Contribution and pull-request workflow](CONTRIBUTING.md)
- [Pull-request submission checklist](.github/PULL_REQUEST_TEMPLATE.md)
- [Testing template](TESTING_TEMPLATE.md)
- [Project notes template](PROJECT_NOTES_TEMPLATE.md)
- [Architecture template](ARCHITECTURE_TEMPLATE.md)
- [AI-use declaration template](AI_USAGE_TEMPLATE.md)

## 3. Mandatory Markdown files — all three are graded

Complete these files at the repository root and include them in your pull request:

- [approach.md](approach.md) — implementation approach, experiments, evidence and decisions (5 marks).
- [challenges.md](challenges.md) — **COMPULSORY**; real challenges, evidence, what you tried, resolution and limitations (5 marks).
- [optimizations.md](optimizations.md) — optimizations considered/implemented, trade-offs and possible improvements (5 marks).

These files must reflect your own actual work. Do not invent problems or measurements. A private hidden chain-of-thought transcript is not required. Empty or generic copy-paste files do not count as a complete submission.

Also submit:

- [TESTING.md](TESTING.md) — fill in actual results for at least five edge cases and document at least five edge cases, their expected outcome, and the actual test/result.
- [DISPATCH_NOTES.md](DISPATCH_NOTES.md) — create this challenge-specific notes file as required by the problem statement.

## 4. Inspect the codebase — do not read only the PDF

Before coding, inspect all source, data, tests and configuration files in this repository:

- `service.py` — main business logic to investigate and improve.
- `models.py` — data shapes and helper functions.
- `fixtures.py` and everything in `data/` — synthetic examples and sample records.
- `main.py` — offline demo and expected execution path.
- Every test file in `tests/` — read the assertions and understand what each test protects.
- `requirements-dev.txt` and `pyproject.toml` — environment and tooling.
- `.github/workflows/` — inspect what the automated checks run on push and pull request.
- `.gitignore` — confirm which files should not be committed.

Do not change a test merely to hide a defect. Add regression tests for fixes. Never upload challenge code or data to external services.

## 5. Run, investigate, and submit

1. Use Python 3.10+ and Git.
2. Install dependencies: `python -m pip install -r requirements-dev.txt`.
3. Run the baseline tests: `python -m pytest -q`.
4. Run the demo: `python -m main`.
5. Investigate failures by tracing the root cause, not by hard-coding fixture output.
6. Re-run tests after meaningful changes and record the actual results in your Markdown notes.
7. Open one pull request from your fork to this original repository. Do not merge it. Make sure all required notes and tests are included.
8. Be ready to explain the implementation and make a small live change if asked.

## Evaluation overview

Total: **100 marks**. The rubric in [STUDENT_PROBLEM_STATEMENT.md](STUDENT_PROBLEM_STATEMENT.md) includes **15 marks for the three mandatory problem-solving documents** (5 marks each). Correctness, edge cases, tests, code quality and the pull request are also assessed.

Challenge-specific context: Logistics: partner eligibility, capacity, ETA calculation, tie-breaking and cancellation handling.
