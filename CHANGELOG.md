# Changelog

## [v3.3] - 2026-05-30

### Changed
- **Dedicated autopay section** - Credit card accounts on autopay that have no payment in
  the window are now listed in their own "AUTOPAY — OUTSIDE WINDOW" section, rather than
  appearing inline in MISSING PAYMENTS with an "(autopay)" suffix (introduced in v3.2).
  This makes the report's three credit card sections: MISSING PAYMENTS,
  AUTOPAY — OUTSIDE WINDOW, and PAYMENTS FOUND.
- `generate_report()` - Now splits missing credit cards into two lists and returns an
  additional `cc_autopay_missing` key.
- `print_report()` - Renders the new section; the inline "(autopay)" suffix has been removed.

### Technical Details
- The header phrasing reflects that these accounts aren't necessarily unpaid — their autopay
  is simply scheduled outside the ±2-week detection window.
- Each section only prints when it has entries, so empty headers never appear.
- Underlying autopay detection (the `#autopay` notes tag) is unchanged from v3.2.

## [v3.2] - 2026-05-30

### Added
- **Autopay account support** - Credit card accounts can be tagged with `#autopay` in their
  Actual Budget account notes to mark them as on autopay
- `is_autopay_account()` - Helper that checks an account's notes field for the `#autopay` tag
- `is_autopay` field added to the `AccountReport` dataclass (defaults to `False`)

### Changed
- `print_report()` - Missing credit card accounts on autopay were initially annotated inline
  as "<account> (autopay)" (this was superseded by the dedicated section in v3.3)
- `config.py` / `config_template.py` - `CERT` now defaults to `True` (validate against
  system CAs) instead of `None`. Newer versions of actualpy raise a TypeError when
  `cert=None` is passed, so `None` is no longer a valid value.

### Technical Details
- Autopay detection reads `account.notes` defensively; if the attribute is missing or
  not a string, the account is simply treated as not-autopay (no crash)
- The `#autopay` tag match is case-insensitive
- Accounts whose notes mention "autopay" in prose but lack the literal `#autopay` tag are
  intentionally NOT flagged (the tag is the deliberate signal)
- This is an additive change; all existing payment-detection logic is unchanged

## [v3.0] - 2026-02-06

### Added
- **Monitored payee support** - Track payments to specific payees (e.g., Target, BMW Financing)
- `MONITORED_PAYEES` config list in config file for specifying which payees to monitor
- `PayeeReport` dataclass for payee payment information
- `find_payee_payment_in_range()` - Check for completed payments to monitored payees
- `find_scheduled_payee_payment_in_range()` - Check for scheduled payments to monitored payees
- Separate report section for monitored payee payments

### Changed
- `generate_report()` - Now returns 4 keys: `cc_missing`, `cc_passed`, `payee_missing`, `payee_passed`
- `print_report()` - Now displays both credit card and monitored payee sections
- Report title changed from "CREDIT CARD PAYMENT REPORT" to "PAYMENT REPORT"

### Technical Details
- Payee matching uses case-insensitive partial name matching
- Looks for negative amounts (money going out) for payee payments
- Supports both completed and scheduled payee payments

## [v2.0] - 2026-02-06

### Added
- **Scheduled transaction support** - Now detects scheduled payments in the Rules table, not just future-dated transactions
- Added `is_scheduled` field to PaymentInfo to distinguish scheduled vs completed payments
- Scheduled payments show with "(scheduled)" marker in the report
- Ignores $0 scheduled transactions (these are reminders, not actual payments)

### Changed
- `find_scheduled_payment_in_range()` - NEW function to check Rules table for scheduled payments
- `generate_report()` - Now checks BOTH completed payments AND scheduled payments
- `print_report()` - Adds "(scheduled)" indicator for future scheduled payments

### Technical Details
- Scheduled transactions are stored as Rules with conditions for date, amount, and account
- Only considers rules with `link-schedule` action and positive amounts
- Only looks at future scheduled dates (not past)

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
