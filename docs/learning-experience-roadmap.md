# Learning experience and visual design roadmap

**Status: pilot implemented on a feature branch; later items are planned.** This page records design intent and acceptance criteria. It does not assert that responsive screenshots, a browser grader or a full AI tutor have already passed validation.

## Review: existing course vs. AI Engineering from Scratch

Reference: [AI Engineering from Scratch](https://aiengineeringfromscratch.com/) ([GitHub](https://github.com/rohitg00/ai-engineering-from-scratch)). Course: [Zynq SDR Course](https://lay007.github.io/zynq-sdr-course/).

Keep our Material for MkDocs, Inter/JetBrains Mono typography, light/dark theme and IEEE-style plots. The current course already has a responsive theme, a hero, cards, two languages and deep lab navigation. However, its first-screen actions emphasize the system document and static figures, while student practice is hard to discover; an extensive sidebar mixes learning routes with reports, quality gates and instructor/reference material.

The reference site separates **curriculum / practice / projects**, annotates level and stage, uses short lead paragraphs, and offers interactive figures with user-controlled parameters. Adopt those information-design ideas, not its pixel-accurate styling, fonts or branding.

## Information architecture

1. **Start learning**: choose simulation-only, RTL-SDR or full Zynq route. Show prerequisites.
2. **Practice**: learner-written starters, local checks, meaningful failure messages, graduated hints.
3. **Measured evidence**: the actual RF/IQ reports, input datasets and limits. Never badge simulation as measured.
4. **Reference**: specification, instructor route, historical bring-up logs and quality gates.

Preserve existing deep links and lab numbers. Do not migrate the long block documentation without an explicit redirect plan.

## Visual language

- The page title names the measurable engineering task, not just the tool.
- A compact metadata strip shows stable exercise ID, level, mode, required hardware and evidence type. Use `planned`/ `manual` / `measured` only when supported.
- Intro describes **input**, **output**, **observed signal** and one expected decision.
- Exercise steps are numbered and visually grouped, but read in the same order without CSS/JavaScript.
- Plots always include axis labels, units, sampling assumptions, captions and an explanation of what changes when a parameter moves.
- Use color as a secondary signal (legend text, symbols and patterns still distinguish traces). Respect Material palette tokens in both themes.
- Prefer stable line charts, spectra, constellation clouds, time-domain waveforms and signal-chain diagrams to decorative photographs.
- Code remains copyable, commands use repository-root paths, and students see a short expected output or error.
- Make focus visible, controls keyboard accessible, motion optional, and layouts readable at 360px and 1280px.
- Avoid gratuitous counters, gamification and certificates unsupported by independent assessment.

## Roadmap

| Phase | Deliverable | Check |
|---|---|---|
| P0 | [FIR/Q15 pilot](practice-fir-q15.md) + local cumulative grader | Good reference passes; untouched starter and three defective variants fail |
| P0 | [Practice track #84](https://github.com/Lay007/zynq-sdr-course/issues/84) | Explicit acceptance, offline dependency path, links to existing labs |
| P1 | [Debugging challenges #85](https://github.com/Lay007/zynq-sdr-course/issues/85) | Wrong CFO sign, IQ mirror, overflow, AXI handshake caught by regression tests |
| P1 | [Visual UX #86](https://github.com/Lay007/zynq-sdr-course/issues/86) | Actual light/dark desktop/mobile screenshots, accessible interactive figures |
| P2 | [Learner tutor #87](https://github.com/Lay007/zynq-sdr-course/issues/87) | Works with Codex/Claude, does not give away answers; manual route still works |
| P2 | [Applied AI for SDR #89](https://github.com/Lay007/zynq-sdr-course/issues/89) | Compare classical DSP and small learned models on independent IQ splits and measured failure cases |

## First UI acceptance gate

Before a visual redesign merges, inspect the **rendered** MkDocs site in light and dark mode at 360px and 1280px. Verify horizontal overflow, keyboard focus, code scrolling, tooltips, nav depth, Russian text wrapping, long signal names, chart contrast and `prefers-reduced-motion`. Keep real RF evidence separate from illustrative simulations. The first PR only introduces small, scoped practice components; large global theme changes belong in #86.

## Attribution and boundaries

The external course is an inspiration for structure, staged learning and test-first pedagogy. Do not copy its code, figures, CSS or editorial assets. Keep public repository content in English, with dedicated Russian learner pages where supported.
