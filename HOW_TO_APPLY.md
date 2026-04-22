# How to apply this bundle

1. Unpack this archive into the root of `zynq-sdr-course`.
2. Review the following new files:
   - `LICENSE`
   - `mkdocs.yml`
   - `.github/workflows/pages.yml`
   - `docs/`
3. Replace the root files with the versions from this archive:
   - `README.md`
   - `README_ru.md`
   - `README_en.md`
4. Commit and push:

```bash
git add .
git commit -m "Add MIT license and publish MkDocs site via GitHub Pages"
git push origin main
```

5. In GitHub open:

`Settings -> Pages -> Build and deployment -> Source -> GitHub Actions`

6. Wait for the workflow to finish. The site URL will be:

`https://lay007.github.io/zynq-sdr-course/`
