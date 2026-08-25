# ADR 0003: Keep board binaries in a dedicated artifact repository

## Status

Accepted — 2026-08-25

## Context

The course publishes hardware claims that depend on exact bitstreams, boot files
and board recovery images. Those files are large, sometimes board-specific and
may embed redistributable vendor IP. Keeping them in the source repository would
make ordinary clones heavy and blur the distinction between reproducible source
and preserved deployment evidence.

The private `zynq-sdr-course-artifacts` repository already stores milestone
bitstreams, boot sets, QSPI backups and original SD-card images. Each entry has a
manifest with hashes, provenance and status.

## Decision

- `zynq-sdr-course` owns source code, lightweight measurement evidence,
  documentation and deterministic rebuild instructions.
- `zynq-sdr-course-artifacts` owns published binary deliverables and irreplaceable
  board recovery data.
- Every artifact directory must have a verified `manifest.json`; documentation
  claims identify the artifact by SHA-256 and source commit.
- Reproducible Vivado project trees and design checkpoints remain generated data
  and are not copied into either repository.
- The course must not require the private repository for simulation, linting,
  documentation builds or vendor-independent HDL tests.

## Consequences

- A normal course clone remains lightweight and usable without private access.
- Published hardware evidence can still be re-hashed and restored exactly.
- Artifact changes require manifest verification independently of source CI.
- Access restrictions on vendor and board-specific binaries remain explicit.
