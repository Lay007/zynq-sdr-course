# Hardware debug by design

Compatibility target for repository-level Markdown asset checks.

The course pages use language-specific documentation files under `docs/ru/` and `docs/en/`. Snippet files in `blocks/` keep relative links that are valid after MkDocs inclusion, while this file lets the raw Markdown asset checker resolve the same local target from the source tree.
