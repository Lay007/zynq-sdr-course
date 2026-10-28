# Community and roadmap maintenance

This is a maintainer checklist for GitHub collaboration features. These features are independent of the MkDocs site and should not duplicate validated lab material. See the [2026-10-28 repository review](reports/repository-review-2026-10-28.md) for the evidence and remaining work behind this snapshot.

## Discussions: first community conversations

**Verified on 2026-10-28:** Discussions is enabled. The GitHub GraphQL API returns Announcements, General, Ideas, Polls, Q&A and Show and tell; Q&A is answerable. The discussion list is empty, so no welcome post has been published or pinned.

Use the existing categories:

- **Q&A** for installation, labs, DSP/FPGA/RF concepts and reproducibility questions; configure as a question-answer category.
- **Ideas** for new labs, alternate hardware routes and curriculum proposals.
- **Show and tell** for learner captures, plots, board bring-up notes and independently reproduced experiments.
- **Announcements** for verified releases, new measured experiments and course milestones (maintainer posts).

The first recommended discussion is the prepared [Welcome to the Zynq SDR Course community](community/WELCOME_DISCUSSION.md). A maintainer should publish it in Announcements and pin it. Verify the live post URL before adding a link to it.

The repository [README](README.md) and [SUPPORT.md](SUPPORT.md) link directly to [Discussions](https://github.com/Lay007/zynq-sdr-course/discussions). Answer general questions there and convert only reproducible defects or agreed tasks into Issues. Keep verified procedures and measurement evidence in MkDocs.

## Projects: one board, not several

**Verified on 2026-10-28:** a signed-out HTTP request to **[Zynq SDR Course: Roadmap](https://github.com/users/Lay007/projects/1)** returned HTTP 200, `public: true`, all seven existing issues (#29, #37, #48, #66, #71, #72, #77), and two views:

1. **All Tasks**, a table.
2. **Development Board**, a board.

The Status field has Backlog, Ready, In Progress, Verification and Done. All seven items are currently Ready. No custom Priority, Area or Validation field was returned. Both views have an empty `groupBy` configuration; the browser interfaces were unavailable, so visual column grouping was not verified. The CLI Project query requires a missing `read:project` scope; the public page supplied the snapshot without changing authentication.

Suggested fields: `Priority` (P1/P2/P3), `Area` (DSP, HDL/FPGA, Hardware/RF, Docs/Course, Infrastructure), `Validation` (Model, RTL, FPGA, RF, Documentation). Do not over-configure initially.

Keep the existing items. These proposals reflect code, reports and issue comments, rather than assuming that every Ready item is unimplemented. They have not been applied to the live Project.

| Issue | Suggested status | Priority | Evidence and remaining acceptance |
| --- | --- | --- | --- |
| [#66](https://github.com/Lay007/zynq-sdr-course/issues/66), QPSK RX DC blocker | Verification | P1 | Persistent estimate implemented and board-tested; [level-step report](reports/hardware/dc-blocker-persist-silicon-20261014.md) still shows residual loss versus DC off. Decide whether that residual meets the issue's goal. |
| [#48](https://github.com/Lay007/zynq-sdr-course/issues/48), OFDM RTL to RF | In Progress | P2 | Fixed-point/RTL and [DMA fabric loopback](reports/hardware/ofdm-dma-fabric-loopback-20261014.md) exist; radio image is built, RF acceptance measurements remain. |
| [#71](https://github.com/Lay007/zynq-sdr-course/issues/71), mailbox RX_STOP | Verification | P2 | RTL and host version handling implemented; simulation/build reported in the issue, board deployment and latency/fragment measurements remain. |
| [#72](https://github.com/Lay007/zynq-sdr-course/issues/72), two-board OTA chat | Backlog | P2 | Plan only; depends on conducted verification of #71, a permitted frequency/power plan and verified RF levels. |
| [#29](https://github.com/Lay007/zynq-sdr-course/issues/29), gain/overload table | In Progress | P2 | [Gain steps](reports/hardware/ad9361-gain-steps-20261014.md) and overload evidence exist; calibrated path S21 and absolute-level limits remain, related to #37. |
| [#37](https://github.com/Lay007/zynq-sdr-course/issues/37), NanoVNA evidence | In Progress | P2 | RU/EN navigation and parser exist; real photos, Touchstone/screenshots and a filled report are missing. This also supplies #29's path calibration. |
| [#77](https://github.com/Lay007/zynq-sdr-course/issues/77), community setup | In Progress | P2 | Discussions/categories, public Project and published Wiki confirmed; welcome/pinning, board triage and repository protections remain. |

Both READMEs already link to the public Project. Add fields or a date-based Roadmap view only when they serve a real workflow. Avoid due dates without a schedule. Review item status against the linked acceptance criteria before changing it.

Project status is workflow progress, not evidence of validation: an item moves to Done only when its acceptance criteria and required verification have been met.

## Wiki publication

At the start of this audit, the separate Wiki at commit `c377ed7` matched all eight managed source pages after newline normalization. Source changes made here await review and a separate maintainer publication with `python tools/publish_wiki.py`. See [Wiki maintenance](wiki/README.md).

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

The read-only API snapshot on 2026-10-28 confirmed secret scanning and push protection enabled, with no open secret-scanning alerts returned. Dependabot alerts and automatic security fixes are disabled, private vulnerability reporting is disabled, code scanning has no analysis, and `main` has neither branch protection nor repository rulesets. Dependabot version-update configuration exists separately. These findings are recorded for maintainer action; this audit did not change access or security settings.

## Insights: review, don't game the metrics

Use **Insights → Pulse, Contributors, Traffic and Dependency graph** (where available) to track real engagement, outside contribution and dependency health. Do not create artificial commits, issues or Discussions to inflate counts.

A useful periodic project review records: new learner questions, reproduced bugs, merged PRs, measured hardware evidence, CI regressions and next verified experiments. Keep numerical claims traceable to a GitHub issue, CI run or report.

Traffic views were accessible through the API on 2026-10-28. No engagement trend or contributor-quality conclusion is inferred from that access; the other Insights panels were not visually reviewed.
