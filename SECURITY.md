# Security Policy

## Supported scope

This repository is maintained as a public DSP/FPGA/SDR engineering course. Security and safety fixes should target the current `main` branch.

## Reporting a vulnerability

Please do not open a public issue for suspected vulnerabilities, accidental secret exposure, private data leaks or unsafe RF procedures.

Report privately through the contact channel listed in the profile README and include:

- affected file, lab or workflow;
- reproduction steps;
- expected impact;
- suggested mitigation, if known.

## Sensitive data

Do not commit:

- API tokens;
- SSH keys;
- passwords;
- VPN credentials;
- private `.env` files;
- real personal data;
- proprietary IQ captures;
- large raw signal records without an explicit dataset policy;
- hardware access credentials.

Use placeholders, manifests and checksums for external datasets.

## RF and hardware safety

Hardware-facing labs should document:

- center frequency and bandwidth;
- TX/RX gain settings;
- RF path and attenuation;
- receiver protection assumptions;
- overload symptoms and corrective actions;
- synthetic-data fallback when possible.

## Dependency and workflow hygiene

Recommended baseline:

- Dependabot for GitHub Actions and Python dependencies;
- strict documentation build;
- HDL simulations through self-checking testbenches when practical;
- generated figures traceable to scripts;
- no private datasets in normal Git history.
