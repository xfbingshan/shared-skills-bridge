# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Cross-platform scheduler support (macOS launchd, Linux cron)
- API documentation (`docs/api.md`)
- Architecture Decision Records (ADR) in design doc

### Refactored
- `bidirectional.py`: extracted generic `_discover_additions`, `_update_baseline`, `_sync_to_shared` to eliminate DRY
- `models.py`: split `parse_frontmatter` into focused helpers (`_strip_bom`, `_extract_yaml_block`, `_parse_scalar_value`, `_parse_multiline_value`, `_parse_yaml_block`)
- `scripts/install.py`: extracted command handlers from `main()` for SRP and OCP
- `adapter.py`: replaced hardcoded platform checks with strategy pattern (`_ADAPTERS` dict)

### Fixed
- Replaced bare `except Exception` with specific exception types in `scanner.py` and `installer.py`
- Fixed duplicate `shared/` subdir in Hermes install path
- Fixed Windows emoji encoding issue in CLI output

## [0.1.0] - 2026-05-10

### Added
- Core modules: `models`, `scanner`, `adapter`, `installer`
- Bidirectional sync: scan Hermes/Kimi for new skills and backfill to shared source
- Baseline tracking (`.hermes-baseline.json`, `.kimi-baseline.json`)
- Windows Task Scheduler integration (`schtasks.exe`)
- CLI with 12 parameters: `--source`, `--target`, `--mode`, `--check`, `--force`, `--bidirectional`, `--update-baseline`, `--install-scheduler`, `--uninstall-scheduler`, `--scheduler-status`, `--interval`
- Example skill: `git-commit-guide`
- 84 unit and integration tests
- Requirements and design documents
