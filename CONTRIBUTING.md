# Contribution workflow

1. Read `STUDENT_PROBLEM_STATEMENT.md` and inspect source code and tests.
2. Create a focused branch, for example `fix/partner-capacity-check`.
3. Run `python -m pytest -q` after each meaningful change. Never delete, skip or weaken tests.
4. Complete the mandatory `approach.md`, `challenges.md`, and `optimizations.md` files from the repository templates; `challenges.md` is explicitly compulsory.
5. Complete `TESTING.md` and `DISPATCH_NOTES.md` as required by the problem statement.
6. Open one pull request from your fork to this original repository. Do not merge it.
7. In the PR describe the root cause, code changes, tests run and known limitations, and mention all three process documents.
8. Check the GitHub Actions test result on the pull request and be ready to explain your code and make a small live modification.

## Documentation quality
The three process files are worth 15 marks total (5 each). Record actual experiments, test evidence, obstacles and trade-offs. Do not invent blockers or performance claims. If you had no major obstacle, state that honestly and describe the hardest edge case you tested. Show your observable engineering rationale rather than a private hidden chain-of-thought transcript. Empty, generic or copied notes do not earn marks.

## Individual-work and AI policy
AI chatbots, AI coding assistants, generated patches/tests and having another person write or debug the solution are prohibited. Ordinary non-AI documentation is allowed. Do not paste challenge code/data into external services. A walkthrough can support integrity checks; an automated detector cannot prove AI use.
