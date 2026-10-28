# Community and roadmap maintenance

This is a maintainer checklist for enabling GitHub collaboration features. These features are independent of the MkDocs site and should not duplicate validated lab material.

## Discussions: enable and welcome

Current setup task: open **Settings → General → Features → Discussions**, enable it and prepare an initial welcome post. Suggested categories:

- **Q&A:** installation, labs, DSP/FPGA/RF concepts and reproducibility questions.
- **Ideas:** proposed labs, alternate hardware routes and curriculum improvements.
- **Show and tell:** learner captures, plots, board bring-up notes and independently reproduced experiments.
- **Announcements:** curated releases, newly validated experiments and course milestones (maintainer posts).

Suggested welcome discussion (pin it):

> **Welcome to the Zynq SDR Course community**
>
> This is a place to ask questions about DSP, fixed-point design, Verilog, Zynq/AD936x and reproducible RF experiments. Start with the [course](https://lay007.github.io/zynq-sdr-course/), [Wiki](https://github.com/Lay007/zynq-sdr-course/wiki) and [FAQ](https://github.com/Lay007/zynq-sdr-course/wiki/FAQ). When asking for help, share your lab, revision, tool versions, expected/observed result and relevant logs. Do not post keys, private data or proprietary IQ recordings.
>
> Use Issues for reproducible bugs or concrete implementation tasks, and Discussions for questions, design choices and results. Hardware reports must state whether they are synthetic, RTL, FPGA-tested or RF-measured.

Once Discussions is enabled, add its direct link to the README and SUPPORT.md; verify it loads before publishing the link.

## Projects: one board, not several

Create a GitHub Project named **Zynq SDR Course: Roadmap**, owned by `Lay007`, make it public and link it to this repository. Use three views:

1. **Board**, grouped by Status: Backlog, Ready, In progress, Verification, Done.
2. **Table**, showing status, priority, area, assignee and linked issue.
3. **Roadmap**, only for work with real target dates (do not invent deadlines).

Suggested fields: `Priority` (P1/P2/P3), `Area` (DSP, HDL/FPGA, Hardware/RF, Docs/Course, Infrastructure), `Validation` (Model, RTL, FPGA, RF, Documentation). Do not over-configure initially.

Seed it with *existing* issues rather than duplicating them:

- [#48](https://github.com/Lay007/zynq-sdr-course/issues/48): OFDM RTL and RF validation.
- [#66](https://github.com/Lay007/zynq-sdr-course/issues/66): QPSK RX DC blocker.
- [#71](https://github.com/Lay007/zynq-sdr-course/issues/71): mailbox RX_STOP latency.
- [#72](https://github.com/Lay007/zynq-sdr-course/issues/72): two-board chat OTA bench.
- [#29](https://github.com/Lay007/zynq-sdr-course/issues/29): AD936x gain/overload evidence.
- [#37](https://github.com/Lay007/zynq-sdr-course/issues/37): NanoVNA evidence and Lab 10 navigation.

Project status is workflow progress, not evidence of validation: an item moves to Done only when its acceptance criteria and required verification have been met.

## Agents: bounded tasks with human review

The GitHub **Agents** tab is for Copilot-supported agent sessions, not community discussion. Use it for narrowly scoped documentation, tests and maintenance tasks with explicit acceptance criteria, such as fixing an existing broken link or adding a test for one HDL block. Repository instructions are in [AGENTS.md](AGENTS.md) and [.github/copilot-instructions.md](.github/copilot-instructions.md).

Always review diffs and CI results yourself. Real board/RF validation requires a real test and an evidence report; an agent-generated assertion is not proof. Agent availability, entitlement and account policies are managed in GitHub settings, not by this repository file.

## Security and quality: inspect actual settings

The repository already contains [SECURITY.md](SECURITY.md) and [.github/dependabot.yml](.github/dependabot.yml). In **Settings → Security and quality / Advanced Security**, review:

- Dependabot alerts and security updates.
- Secret scanning and push protection, if available for this repository.
- Code scanning and any false-positive handling before adding new analysis jobs.
- Private vulnerability reporting.
- Whether the default branch has appropriate review/merge protections.

Do not treat the presence of a configuration file as evidence that a particular alerting or scanning service is enabled. Avoid storing credentials in code or Actions logs.

## Insights: review, don't game the metrics

Use **Insights → Pulse, Contributors, Traffic and Dependency graph** (where available) to track real engagement, outside contribution and dependency health. Do not create artificial commits, issues or Discussions to inflate counts.

A useful periodic project review records: new learner questions, reproduced bugs, merged PRs, measured hardware evidence, CI regressions and next verified experiments. Keep numerical claims traceable to a GitHub issue, CI run or report.
