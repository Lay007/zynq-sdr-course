# ADR 0001: AI-assisted engineering workflow

## Status

Accepted

## Context

The course is developed as a reproducible engineering route for SDR education:

```text
theory -> modeling -> fixed-point -> HDL/FPGA -> RF frontend -> TX/RX -> synchronization -> IQ recording -> electronics -> integrated project
```

AI assistants are useful for routine repository work, but generic prompts often produce inconsistent results: broad rewrites, decorative diagrams, missing validation steps, weak engineering justification, or documentation that is not aligned with the SDR route.

## Decision

The repository will maintain a lightweight AI-assisted engineering layer:

- `CONTEXT.md` for shared project context;
- `.ai-skills/` for reusable engineering procedures;
- this ADR directory for durable workflow decisions.

AI-assisted work should follow these principles:

1. read `CONTEXT.md` before changing the repository;
2. choose the closest skill from `.ai-skills/`;
3. make small reviewable changes;
4. prefer reproducible scripts, figures and checks;
5. report validation commands and limitations;
6. preserve the bilingual engineering nature of the course.

## Consequences

Expected benefits:

- less repeated prompting;
- fewer forgotten quality requirements;
- more consistent labs, figures and CI fixes;
- better reproducibility of AI-assisted changes;
- clearer onboarding for future contributors and AI agents.

Trade-offs:

- the skills must be maintained when the repository structure changes;
- overly rigid skills may need revision for unusual tasks;
- validation still depends on actually running the relevant commands.

## Initial skill set

The initial skill set covers:

- diagnosis before patching;
- lab creation and improvement;
- IEEE-style figures;
- CI repair;
- documentation, navigation and asset verification;
- Verilog verification;
- DSP demo and benchmark-style outputs.
