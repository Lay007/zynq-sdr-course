# GitHub Wiki sources

This directory holds the version-controlled source for the project's GitHub Wiki. It is deliberately separate from the MkDocs course. The course website and `docs/` remain authoritative for laboratory steps, proven results and measured values. The Wiki provides quick access, diagnostic guidance and links, not a second copy of the same material.

## Managed pages

- `Home.md`
- `Getting-Started.md`
- `Hardware.md`
- `DSP-to-FPGA.md`
- `Troubleshooting.md`
- `_Sidebar.md`

## Publishing

GitHub stores each Wiki in a separate Git repository, so changes under this directory do **not** automatically appear in the Wiki. Before the first publication:

1. Open https://github.com/Lay007/zynq-sdr-course/wiki and create an initial `Home` page using the GitHub interface.
2. On a computer with Git and authenticated GitHub push access, run from the main repository root:

```bash
python tools/publish_wiki.py
```

The script clones the separate `Lay007/zynq-sdr-course.wiki.git` repository, replaces only the managed pages, commits changed content and pushes normally (never force-pushes). It does not require a PAT to be placed in source files; standard Git authentication is used. Other Wiki pages remain untouched.

## Maintenance

- Keep public content in English and concise.
- Link to the exact canonical document or report for detailed steps and current measurement data.
- Never claim RF or board validation on the basis of simulation alone.
- Review source changes through the main repository; publish the updated pages after review.
- Avoid unrelated or unverified external links.

Publishing is an explicit maintainer action; it is not a GitHub Pages deployment.
