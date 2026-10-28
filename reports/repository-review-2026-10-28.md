# Repository engineering review: 2026-10-28

## 1. Executive summary

The course has a coherent reference-model, fixed-point, RTL, board and measurement progression. It contains substantial executable and recorded evidence, including a measured two-board QPSK link and an OFDM DMA fabric loopback. Those are different results: OFDM RF acceptance remains open. No architectural rewrite is justified by this review.

This audit fixes documentation and verification gaps: bilingual README claims and navigation, stale community configuration guidance, missing link-check coverage for reports/Wiki/community, a Markdown-only CI formatting gap, and an inaccurate explanation of the DC estimator. The estimator's RTL behavior is unchanged.

The most consequential outstanding repository setting is an unprotected `main` with no repository rulesets. Secret scanning and push protection are enabled, but Dependabot alerts, automatic security fixes and private vulnerability reporting are disabled. Existing DC-blocker, OFDM RF, mailbox latency and RF-path calibration issues remain open. No P0 defect was established within the reviewed scope.

This is a targeted engineering audit with broad inventory and selected deep review, not exhaustive verification of all vendor HDL, MATLAB models, hardware or RF behavior. No board was contacted, no waveform transmitted, no Vivado build launched and no Wiki update published.

## 2. Revision, environment and inventory

- Workspace: `G:/Programs/zynq-sdr-course`, the repository available in this session; the attachment's `D:/Programs/...` path was not used.
- Initial state: clean working tree, local `main` at `69c1f25`.
- `git ls-remote origin HEAD refs/heads/main` and `git fetch origin` established the current remote base, [`6e43ebf`](https://github.com/Lay007/zynq-sdr-course/commit/6e43ebf2de792e78632654fc6dfe37091c7235a0).
- Audit branch: `audit/repository-review-2026-10-28`, created from `origin/main`; local `main` was not advanced or edited.
- Reviewed preceding changes: `e9c2019` (Discussions entry points), `a296c0b` (welcome draft), `6e43ebf` (Project link), `69c1f25` (prose formatting), `432a78b` (Wiki diagrams/FAQ).
- Host: Windows, Python 3.14.0, Icarus Verilog and `vvp` on PATH, authenticated GitHub CLI. `vvp -V` reports runtime `12.0 (devel) (s20150603-1539-g2693dd32b)`. MATLAB R2025a is installed but was not invoked. CI uses Python 3.12 on Ubuntu.

`git ls-files` at the base contains 3,583 tracked files: 875 under `blocks/`, 879 under `docs/`, 1,081 under `hardware/`, 421 under `reports/`, 75 under `tools/`, 74 under `tests/`, 51 under `datasets/` and 25 under `experiments/`. Source inventory: 281 Python, 466 Verilog, 40 SystemVerilog, 57 C, two C++, 14 MATLAB and two Simulink files. These totals include imported hardware sources; they are not counts of independently validated course implementations.

| Location | Role and review boundary |
| --- | --- |
| `blocks/block_01_*` through `block_12_*` | Models, labs, HDL, host/board programs and project briefs; all twelve blocks inventoried |
| `docs/ru/`, `docs/en/`, `mkdocs.yml` | Bilingual wrappers and navigation; strict build and existing navigation/ID checks |
| `hardware/7020_ad936x_sdr/` | Board-specific shell, imported ADI sources, overlays, constraints and rebuild procedures; selected interfaces inspected, vendor tree not exhaustively reviewed |
| `verification/vectors/`, block `tb/` directories | Small deterministic references, captured regression inputs and self-checking benches |
| `datasets/`, `experiments/`, `templates/` | IQ metadata, external/LFS payload references, reproducibility manifests and report contracts |
| `reports/fpga/`, `reports/hardware/` | Existing implementation and measurement records; inspected as historical evidence, not rerun measurements |
| `wiki/`, `community/` | Managed Wiki sources and welcome draft; separate from the published Wiki and Discussions |
| `tools/`, `.github/workflows/` | Task runners, validation tools and Actions workflows; scope and representative execution reviewed |

Ignored local caches, Vivado products and scratch directories exist. They are not tracked defects and were not deleted. Generated plots were rebuilt through scripts, not edited by hand. `tools/tasks.py clean` already protects tracked evidence; no competing cleanup mechanism was introduced.

## 3. What was actually checked

| Area | Review depth | Evidence level reached in this session |
| --- | --- | --- |
| Documentation | READMEs, contribution/support/community guidance, all eight managed Wiki pages, CI matrix, selected course status/evidence pages | Source review, local link/navigation checks and strict MkDocs build |
| Fixed-point | Lab 4.1 FIR, Block 5 four-tap FIR and vector generator, DC estimator, existing OFDM numerical regressions | Source/contract review, deterministic software and selected RTL checks |
| Streaming/control | `axis_iq_passthrough.v`, its bench, mailbox RX_STOP/version handling, `zmbox.c`, OFDM FIFO/radio integration and DMA example | Reset/handshake/latency and CDC source review plus simulations; no new physical timing evidence |
| Measurement chain | QPSK final report, DMA fabric-loopback report, DC A/B measurements, gain/overload and link-layer reports | Consistency review of existing records |
| GitHub | Repository metadata, seven issues and their comment threads (latest progress prioritized), Actions runs/logs, public Project HTML, Discussions GraphQL, separate Wiki Git clone, security API responses | Read-only live service checks; Issue #77 status text corrected separately |
| Security/data | Tracked filenames, selected credential signatures in tracked `.py/.json/.yml/.yaml/.md/.txt/.sh/.c/.cpp` files below 2 MB, Git LFS inventory and dataset/experiment validators | Limited source scan and metadata validation; not a full-history secret or dependency vulnerability audit |

The review does not establish correctness of every algorithm, all parameter values, every reset phase, vendor IP, all clock constraints or all RU/EN prose. It does not establish regulatory permission for the proposed OTA experiment in #72.

## 4. Findings and fixes

Priority meanings: P0 critical, P1 serious, P2 technical improvement or remaining acceptance work, P3 convenience/cosmetic.

| ID | Priority | Evidence and consequence | Disposition |
| --- | --- | --- | --- |
| R1 | P1 | `gh api repos/Lay007/zynq-sdr-course/branches/main/protection` returned `404 Branch not protected`; `/rulesets` returned `[]`. Direct changes can bypass review/required checks. | Open: maintainer should choose and configure branch protections after identifying required checks. No settings changed. |
| R2 | P2 | Repository security metadata and alert endpoints show Dependabot alerts/security updates and private reporting disabled; code scanning returns no analysis. Version-update YAML alone does not provide these controls. | Open: review alerting/private reporting and decide an appropriate analysis scope. Secret scanning/push protection are already enabled. |
| R3 | P2 | [Python Quality run 40681433172](https://github.com/Lay007/zynq-sdr-course/actions/runs/40681433172), job `122792825108`, failed `test_no_em_dash_in_prose` on `COMMUNITY_PLAYBOOK.md` and `SUPPORT.md`. `69c1f25` corrected them, but Markdown is outside `python_quality.yml` path filters. Later green docs jobs did not rerun that test. | Fixed: `docs-assets-check.yml`, which runs on every main push/PR, now runs the existing formatting tests. Full Python workflow filters remain scoped. |
| R4 | P2 | Base `tools/check_markdown_assets.py::iter_markdown_files` omitted `reports/`, `wiki/`, `community/`; `normalize_link` ignored extensionless Wiki page links. A missing Wiki page or broken report link could pass CI. | Fixed: extend the existing checker, including Wiki `.md` resolution and repository-boundary checks. Four regressions added; three failed on the old checker and all pass after the fix. |
| R5 | P2 | Base `COMMUNITY_PLAYBOOK.md` and #77 treated public visibility/categories/Wiki publication as unverified. Signed-out Project data and Discussions/Wiki reads now establish them. `wiki/FAQ.md` still said Discussions was not enabled. | Fixed locally: dated configuration snapshot and evidence-based triage; FAQ links to live Discussions. #77 updated without closing it. |
| R6 | P2 | Both READMEs called all remaining proof points optional, despite #48 RF and #71 board acceptance remaining open. They also claimed every MATLAB lab ran in Python and repeated audience/Wiki/philosophy sections. | Fixed in RU/EN: explicit evidence/limitation table, direct report links, narrower tool requirements, fewer repeated sections and instructor entry point. |
| R7 | P2 | `dc_blocker.v` claimed its growing power-of-two estimator was the exact arithmetic mean. Update weight is `1 / 2^floor(log2(n))`, not `1/n`; a directed Icarus run on `[120, 0, 0]` gives estimate 30 after three inputs, versus arithmetic mean 40. Earlier reset description also conflicted with current `rst_dc` integration. | Fixed comments only: describe the approximation and historical reset configuration. RTL assignments, ports, constants and timing are unchanged. |
| R8 | P1 | Existing [#66](https://github.com/Lay007/zynq-sdr-course/issues/66) and [persistent-DC report](hardware/dc-blocker-persist-silicon-20261014.md) record improvements but residual level-drop loss: 7 gross frames with DC on versus 2 with DC off in the reported comparison. | Open, propose Verification. Do not infer universal correction or close the issue from baseline simulation. |
| R9 | P2 | [#48](https://github.com/Lay007/zynq-sdr-course/issues/48) has [3,072,000 error-free DMA fabric bits](hardware/ofdm-dma-fabric-loopback-20261014.md); the radio image/conditioning stage is simulated and built, not RF-qualified. | Open, propose In Progress. Needs protected RF experiment and complete acceptance metrics. |
| R10 | P2 | [#71](https://github.com/Lay007/zynq-sdr-course/issues/71) comment documents implementation/build and 140 ns simulated RX_STOP-to-TX acceptance. `zynq_message_mailbox_axi_lite.v` exposes version `0x00020001`; `zmbox.c` removes its delay for that version. No new board latency result exists. | Open, propose Verification. Measure conducted chat/fragment latency before OTA work. |
| R11 | P2 | [Gain-step report](hardware/ad9361-gain-steps-20261014.md) shows frequency-dependent nonmonotonic RX steps; [overload report](hardware/ad9361-two-board-overload-20261013.md) records relative limits. Absolute path S21 is still missing; NanoVNA tasks in #37 remain partly unfulfilled. | Open, #29 and #37 In Progress. Calibrate the protected path and publish a filled measurement report. |
| R12 | P3 | `docs/ci-matrix.md` named nonexistent `generate_ieee_plots.yml`, omitted existing CSS/OFDM/mailbox/attribution workflows and described quick preflight as equivalent to Python Quality. | Fixed: actual workflow names/coverage and explicit differences between task runners, Actions and quick preflight. |
| R13 | P2 | `SECURITY.md` excludes private `.env` files from publication, but base `git check-ignore --no-index .env .env.local` returned no matches. Accidental staging had no ignore guard. | Fixed: ignore `.env` and `.env.*`, while allowing a sanitized `.env.example`; verified with `git check-ignore`. No credential file was created or read. |
| R14 | P2 | PR #78 starts the same Block 5 smoke command in Full Course Smoke (job `123050317459`), Block 5 HDL (`123050316241`) and HDL Canonical Vector CI (`123050316100`) on the same head. The three jobs consume separate runner time for overlapping regressions. | Open: consolidate execution/artifact handling in a separate CI change while preserving required checks and parameter coverage. This audit does not remove gates. |

No missing local targets were found in the original README/Wiki entry-point scan or the newly included report/community directory scan. The link work adds missing validation coverage; it is not a claim that broken published URLs were repaired. External links, all Markdown anchors and Mermaid rendering were not exhaustively validated.

## 5. Architecture and numerical assessment

### Evidence progression by component

| Component | Reference/fixed-point/RTL evidence | Existing FPGA/RF/measurement evidence | Remaining boundary |
| --- | --- | --- | --- |
| Blocks 1-3 | IQ, sampling, FFT, mixing, FIR, convolution and decimation models; representative Python labs | Passive receiver datasets where linked | Software success is not hardware implementation evidence |
| Block 4 | Python and MATLAB fixed-point examples, two optional Simulink models | No new target implementation checked here | Toolboxes/model execution and cross-language numerical equivalence not rerun |
| Block 5 | Signed DSP/streaming blocks, deterministic vectors, self-checking benches, mailbox tests | Curated OOC/routed summaries and board reports | Device timing, CDC closure and reset robustness require the exact integrated build |
| Blocks 6-7 | Synthetic RF analysis, gain/capture tools, loopback models | Measured AD936x captures and relative gain/overload reports | No absolute receive-power calibration from dBFS or nominal attenuation alone |
| Block 8 CSS | Bit-exact educational SF7 detector and vector regression | Existing FPGA/OOC reports where indexed | Not a complete interoperable LoRa PHY; separate project owns broader work |
| Block 8 OFDM | Fixed-point models, QPSK/16-QAM, transforms, equalization, conditioning and radio simulations | DMA fabric loopback on a board; radio implementation reports | Fabric loopback excludes the AD936x RF path; #48 still requires RF acceptance |
| Block 9 | CI16/CU8/CF32 readers and synthetic fixtures | LFS-backed or externally referenced recorded captures | Validate format/sample rate, I/Q order, hashes and capture provenance separately |
| Block 10 | Passive design calculations, Touchstone parser, report templates | Required NanoVNA evidence is incomplete (#37) | Synthetic parser self-test is not a measured S11/S21 result |
| Block 11 | Reference chains, QPSK numerical/RTL tests, control/mailbox software | Conducted two-board QPSK and message/link-layer reports | New RX_STOP image, residual DC behavior and OTA plans have separate open gates |
| Block 12 | Project briefs, rubrics and worked references | Reuses specifically linked Block 11 evidence | A framework does not prove each learner project |

### Selected deep review

**Signedness, rounding and saturation.** Block 5 `fir_iq_4tap.v` uses signed Q1.15 inputs/coefficients, a wider accumulator, a signed half-LSB bias and 16-bit output saturation. Its generator uses the same `(value + 2^(SHIFT-1)) >> SHIFT` rule, including negative values. This is round-half-up, not NumPy's ties-to-even rule. Lab 4.1's centered 129-tap software FIR uses `np.round`; it is not the bit-true model of the causal four-tap HDL filter. Those distinct examples must not be asserted equivalent without a shared handoff contract. Parameterized interfaces also do not establish that every width/shift choice is supported.

**Reset, handshake and latency.** `axis_iq_passthrough.v` accepts a new input when its output slot is empty or consumed; registered output data/last remain stable under backpressure. Its self-checking bench drives on negative edges and monitors pre-NBA values at positive edges, avoiding a common one-cycle scoreboard error. Mailbox review traced RX_STOP, its stop-toggle and host version-dependent delay. A simulated 140 ns acceptance is not a board/Linux send-to-ACK latency.

**DC estimator.** The acquisition window grows in powers of two and the accumulator is rescaled when `k` grows. Once `K_MAX` is reached the design is a fixed-weight leaky estimator. `out_i/out_q` remain W-bit differences; this is not a general saturating full-scale subtraction guarantee. The persistent top-level estimate and per-run test resets serve different experiments. The comment correction documents the actual recurrence; choosing a new estimator or overflow policy would need separate numerical/RTL/RF acceptance.

The directed simulation used the default W/K_MAX values, reset, and three consecutive valid I samples with Q zero. The post-update estimates are 120, 60 and 30; the corresponding arithmetic means are 120, 60 and 40. The second and third samples both use `k = 1`, which explains the difference without attributing it to quantization. The scratch bench and output remain under the ignored local audit directory:

```bash
iverilog -g2012 -s tb_dc_mean -o tmp/repository-review-2026-10-28/dc-mean.out blocks/block_05_fpga_hdl_flow/rtl/dc_blocker.v tmp/repository-review-2026-10-28/tb_dc_mean.v
vvp tmp/repository-review-2026-10-28/dc-mean.out
```

```text
After [120,0,0]: estimate=30, arithmetic mean=40
```

**Clock-domain crossings.** `ofdm_async_fifo.v` uses Gray pointers and two-stage synchronizers marked `ASYNC_REG`; the source explicitly requires both sides to reset together. That is an integration contract, not proof for arbitrary unilateral resets. The radio-core benches exercise the sample domain and parameter variants, but simulations cannot establish metastability margins or physical Gray-bus skew. No standalone FIFO bench was found under the expected `tb_ofdm_async_fifo.sv` name. Exact reset release, matched constraints and CDC reports remain a build-specific follow-up; no CDC failure is asserted solely from that absence.

**DMA and libiio.** The OFDM DMA C example intentionally uses locked pages, pagemap and uncached `/dev/mem` access for a teaching bench. Its report records HP0 cache-coherency assumptions and per-symbol `tlast` transfers. This is useful measured board evidence, not a production DMA ownership/cache-maintenance design. libiio capture/configuration paths and AXI4-Lite mailbox control are separate from AXI4-Stream sample transfer. A responsive register does not prove the sample path.

**Language boundaries.** Two C++ teaching examples were inspected; neither was compiled in this Windows session (no host C/C++ compiler found on PATH). Existing Python/RTL tests cover much more of the course than the small C++ examples. MATLAB/Simulink files were inventoried and their optional role checked, but no license/toolbox execution was attempted. No cross-language equivalence or C++ benchmark result is claimed.

## 6. Documentation and maintenance assessment

The main entry points already linked the website, Wiki, Discussions, Issues and Project at the current remote base. `CONTRIBUTING.md` and `SUPPORT.md` already used Discussions correctly; they did not need another rewrite. The corrections concentrate on the remaining stale FAQ/community statements and unsupported README generalizations.

The READMEs now serve learners, FPGA/RF reviewers and instructors/contributors through the initial routing table. Repeated audience, Wiki and philosophy sections were removed. Detailed course navigation, learning routes, reports and RF safety remain linked rather than duplicated. RU/EN changes carry the same requirements and evidence limitations.

The evidence table links the actual [Lab 11.4 final measurement report](../blocks/block_11_integrated_sdr_project/lab_11_4_final_measurement_report.md), rather than the separate generic `docs/final-project-example-report.md` template. Historic reports retain their session-specific numbers and bench counts; they were not rewritten to resemble current test counts.

## 7. Testing and CI/CD assessment

Existing Actions use explicit permissions, scoped triggers and pinned direct Python requirements. Dedicated Block 5, canonical HDL and full-course smoke jobs overlap in baseline coverage. Their duplicate execution on PR #78 was confirmed from live job steps (R14). OFDM also has explicit transform/parameter variants. This audit documents the overlap rather than removing coverage without a separate review of durations, artifacts and required-check configuration.

At the reviewed base, these runs were successful: [Pages 40742243011](https://github.com/Lay007/zynq-sdr-course/actions/runs/40742243011), [Docs Assets 40742242810](https://github.com/Lay007/zynq-sdr-course/actions/runs/40742242810), [Experiment Manifests 40742242665](https://github.com/Lay007/zynq-sdr-course/actions/runs/40742242665), [Attribution 40742242808](https://github.com/Lay007/zynq-sdr-course/actions/runs/40742242808) and [Generate Plots 40742242697](https://github.com/Lay007/zynq-sdr-course/actions/runs/40742242697). The most recent Full Course Smoke in the inspected 30-run window was [40681433161](https://github.com/Lay007/zynq-sdr-course/actions/runs/40681433161), successful at `432a78b`. The Python Quality failure at that revision is explained in R3; later green jobs must not be presented as a successful rerun of it.

Per-workflow latest-run queries through `gh api` additionally confirmed:

| Workflow | Latest main run at checkpoint | Revision / outcome |
| --- | --- | --- |
| Block 5 HDL | [40667978971](https://github.com/Lay007/zynq-sdr-course/actions/runs/40667978971) | `149afc8`, success |
| HDL Canonical Vector CI | [40667978966](https://github.com/Lay007/zynq-sdr-course/actions/runs/40667978966) | `149afc8`, success |
| Block 8 CSS RTL | [39935757068](https://github.com/Lay007/zynq-sdr-course/actions/runs/39935757068) | `97bee8f`, success |
| Block 8 OFDM RTL | [39876349832](https://github.com/Lay007/zynq-sdr-course/actions/runs/39876349832) | `e708e9a`, success |
| Block 8 OFDM RX Chain | [39876349824](https://github.com/Lay007/zynq-sdr-course/actions/runs/39876349824) | `e708e9a`, success |

These are prior branch/path-specific runs, not checks of the audit commit. The GitHub connector did not support the workflow-name run-list endpoints, so those reads used the authenticated CLI.

At PR #78 source commit `a6b4d84`, all seven triggered workflows passed:

| PR workflow | Successful run |
| --- | --- |
| Python Quality | [40754677303](https://github.com/Lay007/zynq-sdr-course/actions/runs/40754677303) |
| Docs Assets Check, including the new formatting gate | [40754677324](https://github.com/Lay007/zynq-sdr-course/actions/runs/40754677324) |
| Commit Attribution Check | [40754677233](https://github.com/Lay007/zynq-sdr-course/actions/runs/40754677233) |
| Experiment Manifests Check | [40754677247](https://github.com/Lay007/zynq-sdr-course/actions/runs/40754677247) |
| HDL Canonical Vector CI | [40754677225](https://github.com/Lay007/zynq-sdr-course/actions/runs/40754677225), 47 testbenches |
| Full Course Smoke | [40754677302](https://github.com/Lay007/zynq-sdr-course/actions/runs/40754677302), strict docs, representative labs and Block 5 HDL |
| Block 5 HDL | [40754677260](https://github.com/Lay007/zynq-sdr-course/actions/runs/40754677260) |

### Tests passed

| Command | Observed outcome |
| --- | --- |
| `python tools/tasks.py docs` | PASS, strict build: 88.42 s at the base and 78.09 s with pinned packages after the edits; informational site-absolute-link messages remain |
| `python tools/tasks.py labs` | PASS, all 20 representative labs in both environments; pinned command wall time 144.06 s; generated summaries and metrics validated |
| `python tools/tasks.py hdl` | PASS, 47 Block 5 testbenches and 8 CSS testbenches on Windows |
| `python tools/run_ofdm_rtl.py` | PASS with pinned Python, 28 testbenches and 3 radio parameter variants; pipelined block-RAM transforms, simulation only |
| `python tools/run_local_ci.py --quick` | PASS, exit 0: Ruff, lab IDs, pytest (381 passed / 1 skipped), all 47 Block 5 and 8 CSS benches, then 28 OFDM benches plus 3 variants |
| `python -m pytest -q` | PASS, 377 passed / 1 skipped before the four new checker tests; one existing Windows pytest-cache warning |
| `python -m pytest -q -p no:cacheprovider` | PASS in the pinned environment: 381 passed / 1 skipped, pytest-reported runtime 280.64 s |
| `python -m pip check` | PASS in the isolated pinned environment, no broken requirements |
| `python -m pytest -q tests/test_docs_formatting.py tests/test_markdown_assets.py -p no:cacheprovider` | PASS, 11 tests after the source/documentation fixes |
| `python -m ruff check blocks tools tests` | PASS |
| `python tools/check_markdown_assets.py` | PASS, including the newly covered reports/Wiki/community |
| `python tools/check_lab_navigation.py` | PASS, no navigation debt |
| `python tools/check_lab_id_registry.py` | PASS |
| `python tools/check_doc_commands.py` | PASS |
| `python tools/check_dataset_manifests.py` | PASS, 33 dataset manifests |
| `python tools/check_experiment_manifests.py` | PASS, 24 experiment manifests |
| `python tools/check_commit_attribution.py --range origin/main..HEAD` | PASS for all seven audit commits |
| `git diff --check origin/main..HEAD` | PASS across the complete audit change |
| CI matrix inventory comparison | PASS, all 21 existing workflow filenames appear in `docs/ci-matrix.md` |
| Directed DC-estimator Icarus run | PASS, observed estimate 30 for `[120,0,0]`; non-comment source tokens also match the base |
| `git check-ignore --no-index .env .env.local` | Both private environment names now ignored; `.env.example` separately confirmed trackable |

Initial runs used the installed environment: NumPy 2.5.3, Matplotlib 3.11.2, MkDocs 1.6.1, Material 9.7.6, PyYAML 6.0.3, pytest 9.1.0, Ruff 0.16.7 and Paramiko 4.0.0. This differs from the direct pins, so it must not be described as a pinned-environment validation.

The separate isolated environment was installed from `requirements-dev.txt` without changing global packages. Final direct versions: NumPy 2.5.4, Matplotlib 3.11.2, MkDocs 1.6.1, Material 9.7.7, PyYAML 6.0.3, pytest 9.1.1, Ruff 0.17.1 and Paramiko 5.1.0. Full pytest, representative labs, strict docs, Ruff, link/navigation/ID/command checks and `pip check` all passed there. Cache-provider suppression in the pinned pytest run avoids the pre-existing Windows cache warning without deleting user caches.

All listed local runs completed successfully. The required `tasks.py hdl` and `run_local_ci.py --quick` commands were both executed to completion, despite their overlapping Block 5/CSS coverage. The second long-window mailbox run passed in 2205.72 s. No in-progress run is counted as a completed result.

The RTL runs emit existing Icarus time-unit/array-sensitivity warnings. PASS means the runner and self-checking benches completed successfully; it does not mean a warning-free HDL lint or a hardware timing check.

### Tests failed

The deliberate pre-fix checker regression run produced three failures and one pass, demonstrating the missing scanner/Wiki coverage. The first patched test run also exposed Windows path separators in test expectations; those expectations were corrected to use `Path.relative_to`. The final status belongs to the subsequent runs, not these diagnostic failures.

No validation failure remains in the final audit runs.

### Tests skipped

The existing native `zmsg` buffer-comparison test is skipped on Windows by its explicit Linux/host-compiler condition in `tests/test_zmsg_once.py`. This is not hardware verification.

### Not tested

- New FPGA synthesis/place-and-route, timing/CDC closure, seed sweeps or bitstream rebuilds.
- New Zynq/AD936x/RTL-SDR/NanoVNA experiments, OTA operation or calibrated RF measurements.
- MATLAB/Simulink execution and standalone C++ builds.
- All OFDM baseline/fabric/16-QAM/long-settling combinations beyond the specific runner commands listed in final results.
- Visual browser rendering of Mermaid, Wiki navigation and Project columns; both browser-control interfaces were unavailable. Public HTTP/API/Git data were used where sufficient.
- A complete external-link/anchor crawl, full-history secret scan or dependency vulnerability audit.

## 8. Wiki, Discussions, Projects and security state

### Published Wiki

`git clone --depth 1 https://github.com/Lay007/zynq-sdr-course.wiki.git ...` succeeded. Published commit `c377ed7447513b303615f41f0101d990cff4bc1e` matched all eight managed source pages at the base after newline normalization. Raw Windows byte comparison initially differed because the separate Wiki checkout uses CRLF; text comparison established there was no content drift. Architecture, FAQ, `_Sidebar.md` and the other managed pages exist.

`tools/publish_wiki.py` checks its allowlisted sources, clones separately, stages only those eight files, avoids a commit on no diff and pushes normally. It does not delete unrelated Wiki pages. The source FAQ/Home changes in this PR are intentionally unpublished. The publishing script itself was reviewed but not executed because its default action commits and pushes the Wiki. Mermaid source was reviewed; graphical rendering remains unverified.

### Discussions and public Project

GraphQL returned the four required categories plus General and Polls, with Q&A answerable, and no discussions. The welcome draft therefore remains unpublished and unpinned. No artificial discussion was created.

The CLI Project query failed with `INSUFFICIENT_SCOPES` for `read:project`. A signed-out `urllib.request.urlopen` request to the exact [Project URL](https://github.com/users/Lay007/projects/1), without credentials or cookies, returned HTTP 200. Its delivered JSON records `public: true`, `All Tasks`/`Development Board`, Backlog/Ready/In Progress/Verification/Done and seven items, all Ready. Pagination says `hasNextPage: false`. No Priority, Area or Validation custom field was returned. Empty view `groupBy` arrays are not treated as visual proof of Status columns.

### Evidence-based issue triage

These are proposed statuses and priorities, not live Project changes. All seven issues remain open. The latest comments were read as well as the issue bodies, because several bodies lag implementation.

| Issue | Proposed status / priority | Progress, dependency and completion gate |
| --- | --- | --- |
| [#29](https://github.com/Lay007/zynq-sdr-course/issues/29) | In Progress / P2 | Relative gain and overload reports exist, including 433/915/2400 MHz gain steps. Needs calibrated path S21/absolute-level interpretation; depends on measurement work also tracked in #37. |
| [#37](https://github.com/Lay007/zynq-sdr-course/issues/37) | In Progress / P2 | Both-language Lab 10.5/10.6 navigation and parser/templates exist. Real bench photos, required NanoVNA exports and filled S11/S21 report linked to Block 11 remain. Synthetic parser fixtures do not satisfy it. |
| [#48](https://github.com/Lay007/zynq-sdr-course/issues/48) | In Progress / P2 | Fixed-point, RTL, DMA board loopback and built radio image exist. Needs protected RF package: BER/counts, EVM/CFO/channel, dBFS, PAPR/back-off, saturation, spectrum and implementation provenance. |
| [#66](https://github.com/Lay007/zynq-sdr-course/issues/66) | Verification / P1 | Persistence fix was board-tested; residual transient loss remains. Review acceptance against both conducted and self-reception cases, with idle-DAC artifact removed. If a new estimator is needed, split that work explicitly. |
| [#71](https://github.com/Lay007/zynq-sdr-course/issues/71) | Verification / P2 | Source, host version guard, simulated abort acceptance and an implementation variant exist. Needs deployed-image provenance, in-flight packet regression and board chat/fragment timing. Private artifact availability may block reproduction. |
| [#72](https://github.com/Lay007/zynq-sdr-course/issues/72) | Backlog / P2 | Plan only. Depends on conducted #71 verification, current permission for frequency/power/bandwidth, antenna/path checks and safe levels. No numeric legal or radiated-power assertion in the issue is approved by this audit. |
| [#77](https://github.com/Lay007/zynq-sdr-course/issues/77) | In Progress / P2 | Public Project, categories and published Wiki now verified; welcome/pin, visual board grouping/triage and security decisions remain. Update the dated snapshot without treating source edits as publication. |

### Security and Insights

Read-only `gh api` responses confirmed secret scanning/push protection enabled and zero open secret-scanning alerts returned; Dependabot alerts disabled (403 with that explicit message), automatic security fixes disabled, private reporting `enabled: false`, code scanning `404 no analysis found`, main protection absent and no rulesets. Those settings are distinct from the weekly Dependabot version-update configuration.

The tracked-filename/signature scan found no candidate private keys or supported token patterns in its stated scope. That does not establish that all historical content is secret-free. No credential value or private IQ payload was copied into this report. Traffic-view access succeeded; Pulse, dependency graph, Contributors and visual settings were not audited, and no activity metrics are inferred.

## 9. Changes delivered

| Files | Change |
| --- | --- |
| `README.md`, `README_RU.md` | Shorter entry points, instructor route, exact hardware/tool wording, linked evidence and open acceptance gates |
| `COMMUNITY_PLAYBOOK.md` | Verified live-state snapshot, issue triage and actual security settings |
| `wiki/FAQ.md`, `wiki/Home.md` | Active Discussions link and prose-format consistency; publication deferred |
| `tools/check_markdown_assets.py`, `tests/test_markdown_assets.py` | Report/community/Wiki coverage and extensionless Wiki validation with regression tests |
| `tests/test_docs_formatting.py`, `.github/workflows/docs-assets-check.yml` | Apply existing prose rule to Wiki/community and run formatting on documentation-only changes |
| `docs/ci-matrix.md` | Current workflow inventory and accurate local/CI scope |
| `blocks/block_05_fpga_hdl_flow/rtl/dc_blocker.v` | Correct estimator/reset comments only |
| `.gitignore` | Ignore private local environment files while allowing a sanitized example |
| `reports/README.md`, this report | Review entry point, evidence, limitations and follow-up plan |

GitHub [Issue #77](https://github.com/Lay007/zynq-sdr-course/issues/77) was updated with the verified progress snapshot and remains open. The original body was re-read before replacement to check for concurrent changes. No other issue is closed, no Project item moved, no Discussion posted, no Wiki published and no merge into `main` performed.

The review is delivered through [PR #78](https://github.com/Lay007/zynq-sdr-course/pull/78). The initial HTTPS push was rejected because the OAuth token lacked `workflow` scope for the CI-file change. The existing SSH access succeeded with batch mode and strict host-key checking; no credential permission was expanded and no force push was used.

Seven focused commits separate environment-file hygiene, documentation checks, bilingual entry points, community guidance, DC-estimator comments, the review report and final validation results. All fourteen changed files are listed above. The working branch targets `main`; the original local `main` remains at `69c1f25`.

## 10. Remaining risks

- Timing margins belong to specific integrated images; some reported variants have small positive slack or a failed default build. A passing unit simulation does not qualify another seed or image.
- The long-window mailbox bench took 2370.13 s in the first local Windows run against its 2400 s minimum timeout; the same bench took 473.34 s in the PR's canonical Linux CI run. The local runtime margin is small. These are simulator wall times, not FPGA latency or throughput measurements; runtime optimization/budget review belongs in a separate test-infrastructure change.
- The QPSK DC estimator still interacts with payload statistics and level transients. Its correction must preserve existing retained-capture and self-reception cases.
- OFDM RF, RX_STOP board behavior and absolute RF calibration remain separate incomplete acceptance gates.
- Some board images and measured raw captures reside outside the public repository. Synthetic LFS replay improves software reproducibility but cannot replace measured raw evidence.
- Parameterized RTL, unilateral FIFO reset, cache/DMA ownership and all tool/version combinations need explicit contracts before reuse outside the tested course configurations.
- Repository protections and dependency alerting require maintainer settings work. This PR cannot supply that protection through documentation alone.

## 11. Follow-up proposals

Effort ranges below are planning estimates, not schedules or benchmark results. They exclude hardware procurement and unavailable-artifact delays.

| Work package | Estimate | Main risk / required acceptance |
| --- | --- | --- |
| Protect main and review security settings (#77) | 0.5-1 maintainer day | Choose required checks that actually run for each PR; verify review bypass policy, dependency alerts and private reporting with a trial PR |
| Conducted RX_STOP verification (#71) | 0.5-1 bench day | Deploy the identified image; repeat no-packet, in-packet stop, ACK collisions, old-version host behavior and 384-byte fragment latency with counts/distributions |
| DC estimator acceptance (#66) | 2-5 engineering/bench days if another algorithm is needed | Define a numeric contract first; compare existing captures, persistent/reset modes, full-scale arithmetic, level steps, CFO and self-reception; RTL regression then timing and controlled RF A/B |
| NanoVNA/calibrated path (#37, #29) | 1-2 bench days | Save calibration plane, Touchstone/CSV/photos/checksums and uncertainty; relate S21 to gain/overload measurements without treating settings as calibrated dBm |
| OFDM radio qualification (#48) | 2-5 bench/analysis days | Attenuated single-board loopback, then independent references; report detection failures, BER denominator, EVM/CFO, spectrum/PAPR and saturation at each point |
| CDC/reset/constraint audit for the exact radio image | 1-3 engineering days | Asynchronous-clock FIFO/reset tests and checked constraint matches; implementation CDC/skew reports and repeated timing; no blanket timing exceptions |
| C/C++ and MATLAB route validation | 1-2 engineering days plus toolbox access | Compile small C++ examples with deterministic fixtures; run the optional Simulink baseline and publish actual versions/tolerances; keep separate from generic Python CI |
| Reduce redundant Actions only after measurement | 0.5-1 engineering day | Record workflow duration/coverage, preserve canonical regressions and parameter variants, then propose a focused deduplication PR |

The immediate order is repository protections and reviewed documentation, #71 conducted verification, path calibration, then OFDM RF or OTA work when its prerequisites are met. Existing issue numbers should be reused instead of creating duplicate tasks.
