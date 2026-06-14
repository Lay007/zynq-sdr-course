# Student CI Grading Guide

This guide explains how to use Git branches and CI checks for student assignments.

## Basic workflow

```text
fork or branch -> implement task -> commit -> push -> CI runs -> green/red result -> review -> fix -> final report
```

## Student branch naming

```text
student/<surname>/<lab-id>
```

Examples:

```text
student/ivanov/lab-5-2-fir-rtl
student/petrov/lab-8-1-cfo
```

## Minimum assignment contract

Every assignment should define:

| Field | Meaning |
|---|---|
| Lab ID | Stable lab or project number |
| Input files | Test vectors, scripts or manifest |
| Expected output | Figure, JSON, text log or report |
| Local command | Command the student can run before push |
| CI check | Workflow or smoke test that validates the task |
| Tolerance | Numeric tolerance when exact match is not expected |

## Local checks before push

```bash
python tools/tasks.py docs
python tools/tasks.py labs
python tools/tasks.py hdl
```

For smaller tasks, run only the relevant block command documented in the lab page.

## Pass/fail interpretation

| CI result | Meaning | Student action |
|---|---|---|
| Green | Required checks passed | Attach report or request review |
| Red | At least one check failed | Read logs, reproduce locally, fix |
| Cancelled | CI did not finish | Re-run after checking workflow status |
| Skipped | Path filters did not trigger | Confirm that the task has the right workflow |

## Instructor checklist

- [ ] The task has a clear expected artifact.
- [ ] The student can reproduce the check locally.
- [ ] The CI result is meaningful and not only a documentation build.
- [ ] The grading rubric is linked when this is a final project.
- [ ] The final answer includes a short engineering conclusion.
