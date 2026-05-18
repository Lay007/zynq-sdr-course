# Skill: Fix CI Safely

Use this skill for GitHub Actions failures, smoke checks and reproducibility regressions.

## Goal

Restore CI with the smallest safe change while keeping local commands and GitHub Actions aligned.

## Procedure

1. Read the failing job, step and exact command.
2. Classify the failure:
   - dependency/install issue;
   - MkDocs strict build;
   - broken link or missing image;
   - generated asset mismatch;
   - Python lab failure;
   - Verilog simulation failure;
   - permission or GitHub token issue.
3. Prefer fixing the source of the problem, not only the workflow.
4. Keep local and CI commands consistent.
5. Add a narrow check when the same error could return.
6. Avoid changing unrelated workflows in the same patch.

## Common commands

```bash
python tools/tasks.py docs
python tools/tasks.py labs
python tools/tasks.py hdl
python tools/tasks.py smoke
```

## GitHub Actions rules

- Do not add write permissions unless the workflow truly needs to push or create releases.
- If a workflow auto-commits generated assets, document why `contents: write` is needed.
- Do not hide failures with `|| true` unless the step is intentionally advisory and documented.
- Prefer deterministic generated outputs.

## Output format

Report:

- failing job/step;
- root cause;
- changed files;
- validation command;
- CI risk that remains.
