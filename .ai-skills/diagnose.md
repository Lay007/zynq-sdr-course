# Skill: Diagnose Before Patching

Use this skill for failures in CI, MkDocs, generated assets, Python labs, Verilog tests, links or images.

## Goal

Find the smallest true root cause and fix it without broad rewrites.

## Procedure

1. Read the exact error message first.
2. Identify the failing subsystem:
   - MkDocs/navigation;
   - image or link path;
   - generated asset;
   - Python lab;
   - Verilog testbench;
   - GitHub Actions permissions or environment.
3. Reproduce with the narrowest local command when possible.
4. Inspect the nearest source file before changing anything.
5. Form one root-cause hypothesis.
6. Make the smallest safe patch.
7. Run the closest validation command.
8. If the failure is a regression, add or improve a check so it is caught earlier next time.

## Preferred validation commands

```bash
python tools/tasks.py docs
python tools/tasks.py labs
python tools/tasks.py hdl
python tools/tasks.py smoke
```

Use the narrowest command first, then a broader command if the change touches shared infrastructure.

## Output format

Report:

- root cause;
- changed files;
- validation command;
- result;
- follow-up risk if anything could not be checked.

## Do not

- rewrite unrelated pages;
- silence warnings without understanding them;
- delete generated assets unless the generator is also updated;
- change CI permissions broadly unless the failure is proven to be permission-related;
- claim validation passed if the command was not run.
