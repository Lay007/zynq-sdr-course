# Learning practice validation, 2026-11-13

## Scope and provenance

Local preparation for [issue #85](https://github.com/Lay007/zynq-sdr-course/issues/85)
and the FIR/Q15 pilot in [issue #84](https://github.com/Lay007/zynq-sdr-course/issues/84).
Base: `d26b52a`. The existing pilot was taken from
[PR #88](https://github.com/Lay007/zynq-sdr-course/pull/88), head
`5bc84340f71935841b7463be85d01cb7f08c5703`, and integrated into the current working
diff with the diagnostic exercises. This report records the local validation
checkpoint before commit and integration. No Wiki publication or board deployment
was performed.

## Changes

- `practice/diagnostics/`: learner-owned Python/Verilog copies, a report template,
  metadata, local grader, instructor references and deliberate defects.
- Four diagnostic cases: CFO correction sign, swapped/conjugated IQ, FIR
  accumulator/output overflow and wrong Q format, AXI loss/duplication.
- `practice/fir-q15/`: the existing three-stage pilot, strengthened with explicit
  impulse, zero-input, signed endpoint, accumulator-width and half-LSB checks.
- Fixed a false pass in the pilot's float comparator. A candidate returning only
  `NaN` passed stage 1 because `abs(NaN - expected) > tolerance` is false. The new
  CLI regression failed before the fix; explicit finite-value validation rejects
  it afterward. Positive and negative infinity are also rejected.
- The pilot identifies instructor-reference checks and prints the source SHA-256.
  Instructor checks do not record learner completion.
- Diagnostic JSON includes source/grader hashes, seed, evidence level and metrics;
  RTL includes testbench hash, Icarus version and simulation log. Tool exceptions
  replace stale success reports with an incomplete failure report.
- Paired RU/EN guides, shared practice navigation, entry-page links and the pilot
  UI components from PR #88. The two FIR exercises explicitly document their
  different rounding contracts: nearest-even versus the Block 5 ties-up rule.
- A dedicated diagnostic CI workflow and diagnostic controls in local HDL
  preflight. Local software preflight now lints the practice directory.

## Commands actually run

Windows used the repository `.venv` (Python 3.12.13). WSL Ubuntu used Python
3.12.3 and Icarus Verilog 12.0. The commands below are relative to the repository
root; the actual Windows invocation used `.venv/Scripts/python.exe`.

| Command | Result |
| --- | --- |
| `python tools/run_local_ci.py --software-only` | Ruff for blocks/tools/tests/practice, lab registry, 432 tests passed, 5 skipped |
| `python practice/fir-q15/check.py --stage 3 --solution` | All three cumulative reference stages passed; instructor mode identified |
| `python -m pytest tests/test_practice_fir_q15.py -q` | 9 pilot tests passed after the NaN fix |
| `python -m pytest tests/test_diagnostic_challenges.py -q` (WSL) | 18 tests passed, including actual RTL simulation |
| `python practice/diagnostics/check.py self-test --with-rtl --output build/diagnostics-controls.json` (WSL) | Four references accepted, ten defective variants rejected |
| `python tools/tasks.py docs` | MkDocs strict build passed |
| `python tools/check_doc_commands.py` | Documented command check passed |
| `python -m pytest tests/test_docs_formatting.py tests/test_markdown_assets.py tests/test_lab_navigation.py -q` | 15 tests passed |
| `git diff --check` | No whitespace errors |

The Windows diagnostic test skips RTL when Icarus is not on the Windows `PATH`;
the WSL run above executes that test. The broad software suite's five skips are
not counted as passes. The full `--quick` HDL suite was not run: the production
RTL was unchanged, and the new AXI testbench was exercised directly in WSL.
GitHub Actions has been configured, not executed by this local validation.

## Observed negative controls

| Defect | Evidence from the deterministic checks |
| --- | --- |
| Wrong CFO correction sign | +2750 Hz produces approximately +5500 Hz residual CFO and bit errors |
| No CFO correction | Nonzero positive/negative frequency cases fail; zero CFO alone is insufficient |
| Swapped IQ / conjugated IQ | Both signed-tone cases and complex endpoint comparisons fail |
| 32-bit FIR accumulator wrap | Small-signal cases pass; positive/negative overload and endpoint cases fail |
| Wrong FIR Q shift | Impulse, ties, small-signal scaling and overload checks fail |
| Final FIR output wrap | Overload/endpoint checks fail |
| Reversed taps | Asymmetric impulse response fails |
| AXI stalled-register overwrite | `DIAGNOSTIC_FAIL: stalled output changed at cycle 4` |
| AXI stale output valid | `DIAGNOSTIC_FAIL: output without accepted input (duplicate), cycle 11` |

The AXI reference delivered 64 post-reset samples exactly once, with 52 stalled
cycles, 105 input-bubble cycles (including drain time), and 57 simultaneous
input/output transfers across the experiment. Reset interrupted a pending output.
These are simulation counts, not FPGA latency or throughput measurements.

## Remaining limits

- Rendered visual QA is incomplete. Edge headless capture timed out after 45 s;
  Playwright package download timed out; the connected browser host reported
  `The browser access host is unavailable`. A native browser capture could not
  target the minimized window. No 360px/1280px, light/dark screenshot or keyboard/
  contrast/reduced-motion pass is claimed. PR #88's visual gate remains open.
- No new RF, board, synthesis, timing, resource or ARM performance evidence.
- No interactive browser DSP figure, filterable catalog, learner AI tutor or IQ
  machine-learning benchmark was implemented. These remain separate issue scopes.
- Passing these public deterministic cases does not prove arbitrary-input
  correctness or student understanding. The learner report still needs an actual
  prediction, diagnosis, measured failure and explanation of the fix.
- Generated detailed JSON/logs are local under `build/`; they are not published.
