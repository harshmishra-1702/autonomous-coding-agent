# Evaluation results

Run with `python -m evals.run_evals --runs 3`. Each task is checked by running the result in the sandbox.

## Baseline (Day 14)

- Date: 20-10-26
- Models: Groq openai/gpt-oss-20b, fallback Google gemini-3.8-flash
- Score: <28/30> (from the Score line)
-------------------------------------------
| Task                | Passed | Avg time |
|---------------------|--------|----------|
| fizzbuzz            | 3/3    | 5s       |
| stdin_sum           | 3/3    | 8s       |
| fix_bug             | 2/3    | 26s      |
| small_edit          | 3/3    | 44s      |
| add_with_test       | 3/3    | 21s      |
| fix_failing_test    | 2/3    | 57s      |
| rename_across_files | 3/3    | 52s      |
| csv_total           | 3/3    | 31s      |
| distinct_words      | 3/3    | 13s      |
| edit_similar_lines  | 3/3    | 45s      |
-------------------------------------------

## Notes

 error: BadRequestError: Error code: 400 - [{'error': {'code': 400, 'message': 'Function call is missing a thought_signature in functionCall part
 error: BadRequestError: Error code: 400 - {'error': {'message': "Parsing failed. The model generated output that could not be parsed. Please adj



## After LLM-layer fixes (Day 15)

- Fixes: placeholder thought signatures when failing over to Google, retry on Groq parse failures.
- Score: 26/30 (baseline 28/30)
- No API errors reported this run. Failures: fix_failing_test (1), rename_across_files (2), csv_total (1), not yet diagnosed.
- With 3 runs per task, a 2-point difference is within noise.

| Task | Passed | Avg time |
|---|---|---|
| fizzbuzz | 3/3 | 7s |
| stdin_sum | 3/3 | 10s |
| fix_bug | 3/3 | 17s |
| small_edit | 3/3 | 34s |
| add_with_test | 3/3 | 17s |
| fix_failing_test | 2/3 | 49s |
| rename_across_files | 1/3 | 35s |
| csv_total | 2/3 | 20s |
| distinct_words | 3/3 | 11s |
| edit_similar_lines | 3/3 | 19s |

## After tool path fix and step budget (Day 16)

- Changes: empty path accepted by list_dir, default step limit 10 to 15, warning two steps before the limit, prompt rule to stop once code works.
- Eval change: csv_total wording now asks for only the number, so that task is not directly comparable to earlier runs.
- Score: 29/30 (Day 15: 26/30, Day 14: 28/30). A targeted run of the three weakest tasks scored 9/9.
- Remaining weak spot: fix_failing_test (2/3, slowest task at 85s average).

| Task | Passed | Avg time |
|---|---|---|
| fizzbuzz | 3/3 | 4s |
| stdin_sum | 3/3 | 8s |
| fix_bug | 3/3 | 19s |
| small_edit | 3/3 | 19s |
| add_with_test | 3/3 | 20s |
| fix_failing_test | 2/3 | 85s |
| rename_across_files | 3/3 | 48s |
| csv_total | 3/3 | 26s |
| distinct_words | 3/3 | 16s |
| edit_similar_lines | 3/3 | 18s |


## Findings from trajectory reports (Day 17)

- Trajectory reports of three fix_failing_test runs showed 12 to 15 steps each. Two causes: pytest is not installed in the sandbox and the agent tried it 2 to 3 times per run, and history compaction fired on every step from step 6 on tiny files because the context budget was set far too low, so old tool outputs became stubs and the agent kept re-reading files.
- Fixes: context budget set to 24000 characters, and a system prompt line stating the sandbox has no pytest, no internet and no pip installs.
- Result: fix_failing_test went to 3/3 in two separate targeted runs (6/6 total) at 26 to 28s average (earlier full runs: 2/3 at 49 to 85s).
- Caveat: these are targeted runs of a single task. A full re-run is needed for a new overall baseline.
- Tooling: `python -m evals.report <run folder>` prints any run as one line per step. Failed runs and runs that hit the step limit now print it automatically.