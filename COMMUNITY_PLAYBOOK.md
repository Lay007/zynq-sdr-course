# Community and roadmap maintenance

This is a maintainer checklist for enabling GitHub collaboration features. These features are independent of the MkDocs site and should not duplicate validated lab material.

## Discussions: first community conversations

**Verified on 2026-10-28:** Discussions is enabled in repository settings. Category names, the welcome post and pin status have not been independently verified.

Configure or confirm these categories in the GitHub interface:

- **Q&A** for installation, labs, DSP/FPGA/RF concepts and reproducibility questions; configure as a question-answer category.
- **Ideas** for new labs, alternate hardware routes and curriculum proposals.
- **Show and tell** for learner captures, plots, board bring-up notes and independently reproduced experiments.
- **Announcements** for verified releases, new measured experiments and course milestones (maintainer posts).

The first recommended discussion is the prepared [Welcome to the Zynq SDR Course community](community/WELCOME_DISCUSSION.md). Publish it in Announcements and pin it after the actual category is created. Verify the live post URL before adding a link to it.

The repository [README](README.md) and [SUPPORT.md](SUPPORT.md) link directly to [Discussions](https://github.com/Lay007/zynq-sdr-course/discussions). Answer general questions there and convert only reproducible defects or agreed tasks into Issues. Keep verified procedures and measurement evidence in MkDocs.

## Projects: one board, not several

The maintainer has created **[Zynq SDR Course: Roadmap](https://github.com/users/Lay007/projects/1)** under `Lay007` and imported seven existing issues (#29, #37, #48, #66, #71, #72, #77), as confirmed by a GitHub UI screenshot. The exact Project URL was supplied on 2026-10-28. **Public visibility has not been independently verified**; confirm it without signing in before marking publication complete. Use three views:

1. **Board**, grouped by Status: Backlog, Ready, In progress, Verification, Done.
2. **Table**, showing status, priority, area, assignee and linked issue.
3. **Roadmap**, only for work with real target dates (do not invent deadlines).

Suggested fields: `Priority` (P1/P2/P3), `Area` (DSP, HDL/FPGA, Hardware/RF, Docs/Course, Infrastructure), `Validation` (Model, RTL, FPGA, RF, Documentation). Do not over-configure initially.

Seed the board with *existing* issues rather than duplicating them. Suggested **initial triage** below is not a claim about current progress. Start each item in Backlog unless the maintainer confirms its actual status.

| Issue | Area | Suggested priority | Validation needed |
| --- | --- | --- | --- |
| [#66](https://github.com/Lay007/zynq-sdr-course/issues/66), QPSK RX DC blocker | HDL/FPGA | P1 | RTL + RF measurements |
| [#48](https://github.com/Lay007/zynq-sdr-course/issues/48), OFDM RTL to RF | HDL/FPGA | P2 | RTL, FPGA, then RF |
| [#71](https://github.com/Lay007/zynq-sdr-course/issues/71), mailbox RX_STOP | HDL/FPGA | P2 | FPGA timing and link-layer measurements |
| [#72](https://github.com/Lay007/zynq-sdr-course/issues/72), two-board OTA chat | Hardware/RF | P2 | Safe, permitted RF experiment |
| [#29](https://github.com/Lay007/zynq-sdr-course/issues/29), gain/overload table | Hardware/RF | P2 | Repeatable RF measurement |
| [#37](https://github.com/Lay007/zynq-sdr-course/issues/37), NanoVNA evidence | Docs/Course | P3 | Measurement artifacts and documentation |
| [#77](https://github.com/Lay007/zynq-sdr-course/issues/77), community setup | Infrastructure | P2 | Links and configuration verified in GitHub UI |

When publishing the Project, capture its exact public URL and add it to both READMEs. Do not invent a Project number. Avoid adding due dates without a real schedule. A first board with 5 workflow statuses is more useful than many custom views.

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
