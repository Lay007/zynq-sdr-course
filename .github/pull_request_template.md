## Summary

Describe the problem, the change and its effect on the course.

## Validation

List the commands, simulations or measurements used to validate the change.

```text
python tools/tasks.py docs
python tools/tasks.py labs
# python tools/tasks.py hdl   # for HDL changes
```

## Evidence

- [ ] Results are reproducible from the repository root.
- [ ] Generated plots, metrics or hardware artifacts are included or linked.
- [ ] Synthetic and real measurements are clearly distinguished.
- [ ] RF-facing changes document frequency, gain, attenuation and safety assumptions.

## Documentation

- [ ] New lab pages are represented in `mkdocs.yml` or explicitly excluded.
- [ ] Russian and English course paths remain consistent.
- [ ] Units, fixed-point formats and engineering assumptions are stated.
- [ ] Relevant status, index or readiness documents are updated.

## Commit quality

- [ ] Commits are focused and have descriptive messages.
- [ ] No generated secrets, credentials or large non-LFS captures are committed.
- [ ] AI tools are not listed as commit co-authors.
