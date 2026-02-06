# Changelog

## [v1.2] - 2026-02-06

### Changed
- Split code into modular structure:
  - `cc_payment_report.py` - Reusable library module with all core functions
  - `run_report.py` - Thin wrapper that imports and calls the library
- This allows for easier testing and potential reuse of the library functions

### Added
- CHANGELOG.md for version tracking

## [v1.1] - 2026-02-05

### Changed
- Renamed main Python script from `cc_payment_report.py` to `run_report.py`
- Updated bash script to call `run_report.py`
- Added Python warning suppression flag `-W ignore::UserWarning` to eliminate multi-line migration warnings from email reports

### Fixed
- Migration warnings from actualpy no longer appear in email reports
- Cleaner email output

## [v1.0] - 2026-02-05

### Added
- Initial release
- Credit card payment detection via Payees table
- Support for Actual Budget's integer date format (YYYYMMDD)
- One-line payment output format
- Bash wrapper script with Mailgun email integration
- Healthcheck monitoring support
- Config file separation for security
- Zero-balance account filtering
- None-balance account filtering (for closed accounts)

### Features
- Detects payments as transfers where payee has `transfer_acct` set
- Checks ±2 weeks from current date
- Excludes accounts with zero or None balances from missing payments list
- Email subject shows ✅ or ❌ based on success/failure
- Timestamps report output files for debugging
