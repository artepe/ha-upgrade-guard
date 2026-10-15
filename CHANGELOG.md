# Changelog

## v0.1.0 — 2026-10-15

- Read-only Home Assistant REST API snapshots
- Privacy-conscious normalization of entity state and capabilities
- Before/after diff: removed, new, degraded, recovered and capability changes
- Self-contained offline HTML report, Markdown and machine-readable JSON
- Configurable ignore patterns and CI-friendly fail thresholds
- No-install `guard.py` command and optional console entrypoint
- Automated tests on three Python versions

**Known limitations:** point-in-time snapshots, no live flapping detection, no registry-based rename matching, no HACS panel.
