# Skill: Verify Docs, Navigation and Assets

Use this skill when images do not render, MkDocs navigation is inconsistent, links are broken or pages exist but are not visible.

## Goal

Keep GitHub README, MkDocs pages, images and navigation consistent.

## Procedure

1. Identify where the asset/page should render:
   - GitHub README;
   - MkDocs page;
   - bilingual EN/RU block;
   - generated demo dashboard.
2. Check the actual path and filename case.
3. Check relative path from the markdown file location.
4. Check whether the file exists in the repository.
5. Check whether the page is listed in `mkdocs.yml` when it should appear in navigation.
6. Check whether generated assets are produced by scripts or committed as static files.
7. Patch the smallest source of inconsistency.
8. Run the docs build when possible.

## Common failure modes

- path works from README but not from nested docs page;
- filename case differs between Windows and Linux;
- image exists as `.jpg` but markdown references `.png`;
- generated asset is ignored by `.gitignore`;
- page exists under `docs/` but is missing from `mkdocs.yml`;
- bilingual paths drift between `docs/en` and `docs/ru`.

## Validation

```bash
python tools/tasks.py docs
```

If image generation is involved:

```bash
python tools/tasks.py labs
python tools/tasks.py docs
```

## Output format

Report:

- broken reference;
- corrected path or navigation entry;
- affected pages;
- validation command and result.

## Do not

- duplicate the same image into many folders unless necessary;
- rename assets without updating every reference;
- remove pages from navigation to silence warnings unless they are intentionally hidden;
- assume Windows path behavior matches Linux CI.
