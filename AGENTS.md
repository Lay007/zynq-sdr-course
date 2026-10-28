# Repository instructions for coding agents

This repository is a bilingual, evidence-oriented SDR/DSP/FPGA course, not a generic demo. Read [CONTEXT.md](CONTEXT.md) and [CONTRIBUTING.md](CONTRIBUTING.md) before a substantive change.

## Engineering contract

- Preserve the progression: reference model → fixed-point → HDL/testbench → FPGA → RF experiment → measurement/report.
- Never conflate synthetic, simulation, RTL, FPGA timing/board, and measured RF results. State the actual evidence level.
- Maintain the current Zynq-7020/AD936x assumptions only where they are applicable; do not invent board pin mappings, clock settings, experiment results or benchmark figures.
- For HDL changes, check reset and handshake timing, signedness, scaling, latency, clock-domain crossings and deterministic test vectors.
- For RF-facing material, document gain, frequency plan, receiver safety, attenuation and IQ metadata. Do not recommend unverified direct TX-to-RX connections.
- Public code comments, commit messages, Wiki content and new issue/PR text are in English; maintain RU/EN course pages consistently when changing course content.
- Comments should explain *what* was changed and *why*, not narrate routine code line-by-line. Avoid boilerplate and inflated claims.
- Do not put secrets, private IQ captures or unpublished board artifacts into the public repository.
- Never add an AI co-author trailer or claim that a tool validated hardware unless it actually did.

## Scope and verification

Prefer small, reviewable changes that address a stated issue. Inspect existing tests before editing. Do not refactor unrelated code or rewrite generated figures manually.

Common checks from the repository root:

```bash
python tools/tasks.py docs
python tools/tasks.py labs
python tools/tasks.py hdl
python tools/run_local_ci.py --quick
```

Choose checks relevant to the changed files. For docs-only edits, use the strict docs build when the environment supports it. In a final report or PR, list commands actually run, outcomes, limitations and the changed files.

For GitHub Wiki changes, edit tracked sources under `wiki/`. Wiki publication is a separate maintainer operation using `python tools/publish_wiki.py`; do not silently publish or overwrite unrelated Wiki pages.
