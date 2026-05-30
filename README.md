# Credit Card Payment Report

A Python tool for [Actual Budget](https://actualbudget.org/) that checks whether your
credit card accounts (and selected payees) have received payments within a 4-week window
(±2 weeks from today), and reports any that appear to be missing. Designed to run on a
schedule and email the results.

## Features

- **Credit card payment detection** — Finds payments to accounts named with a `💳` prefix
  by detecting transfers (via the Payees `transfer_acct` field).
- **Scheduled transaction support** — Detects future payments entered as Actual *scheduled
  transactions* (stored in the Rules table), not just future-dated transactions. Payments
  found this way are marked `(scheduled)`. Zero-dollar schedules are ignored (they are
  treated as reminders).
- **Monitored payee support** — Tracks payments to arbitrary payees (e.g. `Target`,
  `BMW Financing`) configured in `config.py`, reported in their own section.
- **Autopay annotation** — Credit card accounts tagged `#autopay` in their Actual account
  notes are annotated with `(autopay)` when flagged as missing. This helps distinguish a
  genuinely missed payment from an autopay that is simply scheduled more than two weeks out.
- **Email + monitoring** — A companion bash script emails the report via Mailgun and pings
  a [Healthchecks.io](https://healthchecks.io/) URL for success/failure monitoring.

## Version History

See `CHANGELOG.md` for full details. Highlights:

- **v3.2** — Autopay account annotation (`#autopay` tag in notes); `CERT` config fix.
- **v3.0** — Monitored payee support.
- **v2.0** — Scheduled transaction (Rules table) support.
- **v1.x** — Initial credit card payment detection, modular structure, warning suppression.

## Installation

```bash
python -m venv venv
source venv/bin/activate        # on Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

The project uses two config files, both gitignored because they contain secrets. Copy the
templates and fill in your values.

### 1. Python config (`config.py`)

Copy `config_template.py` to `config.py`:

```python
BASE_URL = "https://your-actual-server:5006"   # Your Actual server URL
PASSWORD = "your_password"                       # Server password
FILE = "My Budget"                               # Budget name, ID, or Sync ID
ENCRYPTION_PASSWORD = None                        # Set if your budget is encrypted
DATA_DIR = None                                   # Optional local data directory

# SSL certificate verification:
#   True  = validate against system CAs (correct for a real cert, e.g. LetsEncrypt)
#   False = skip verification (use for self-signed certs)
#   "/path/to/cert.pem" = validate against a specific cert/CA bundle
# Do NOT use None -- newer versions of actualpy raise a TypeError.
CERT = True

# Payees to monitor for payments (case-insensitive partial match)
MONITORED_PAYEES = [
    "Target",
    "BMW Financing",
]
```

> **Note on `CERT`:** If your server is fronted by a reverse proxy with a valid certificate
> (e.g. Caddy/LetsEncrypt), use `CERT = True`. Older versions of this project used
> `CERT = None`, which now crashes with newer actualpy releases.

### 2. Marking accounts as autopay

There is no setting for autopay in `config.py`. Instead, add the tag `#autopay` anywhere in
an account's **Notes** field inside Actual Budget. Accounts tagged this way are annotated
with `(autopay)` in the report when they would otherwise be flagged as missing. The match is
case-insensitive, and the literal `#autopay` tag is required — prose like "autopay on the
5th" without the tag is intentionally ignored.

### 3. Email/automation config (`cc_payment_check.config`) — optional

Only needed if you want scheduled email reports. Copy
`cc_payment_check.config.template` to `cc_payment_check.config`:

```bash
HEALTHCHECK_URL="https://hc-ping.com/YOUR_ID/cc-payment-report"
MAILGUN_API_KEY="YOUR_MAILGUN_API_KEY"
MAILGUN_DOMAIN="mg.yourdomain.com"
EMAIL_TO="you@example.com"
EMAIL_FROM="Credit Card Report <noreply@mg.yourdomain.com>"
SCRIPT_DIR="/home/pi/cc_payment_report"
VENV_PATH="/home/pi/venv/bin/activate"
REPORT_OUTPUT="/tmp/cc_payment_report_$(date +%Y%m%d_%H%M%S).txt"
```

## Usage

### Run the report directly

```bash
python run_report.py
```

### Run via the email/automation wrapper

```bash
./cc_payment_check.sh
```

This runs the report, emails it via Mailgun (subject prefixed ✅ or ❌ depending on
success), and pings your Healthchecks.io URL.

### Schedule it (cron, weekly Monday 8 AM)

```cron
0 8 * * 1 /home/pi/cc_payment_report/cc_payment_check.sh >> /home/pi/cc_payment_report/cron.log 2>&1
```

## Output Example

```
🔍 Checking for payments between 2026-05-16 and 2026-06-13
📅 Report run date: 2026-05-30

💳 Found 24 credit card accounts
👤 Checking 2 monitored payee(s)

================================================================================
PAYMENT REPORT
================================================================================

💳 CREDIT CARD PAYMENTS
--------------------------------------------------------------------------------

⚠️  MISSING PAYMENTS
  • 💳 BofA Susan 1.5
  • 💳 Chase Amazon (autopay)

✅ PAYMENTS FOUND
  • 💳 Chase United | 2026-05-21 | $1,345.87 | PAYMENT TO CHASE CARD
  • 💳 Discover Larry | 2026-06-12 | $248.62 (scheduled)

👤 MONITORED PAYEE PAYMENTS
--------------------------------------------------------------------------------

⚠️  MISSING PAYMENTS
  • BMW Financing

✅ PAYMENTS FOUND
  • Target | 2026-05-24 | $152.31

================================================================================
```

## How It Works

1. Connects to your Actual Budget server using actualpy.
2. **Credit cards:** finds all accounts whose name starts with `💳`. For each, it looks for
   a payment within ±2 weeks — first as a completed/future-dated transfer, then (if none) as
   a scheduled transaction in the Rules table. Accounts with a `None` or `0` balance are
   excluded from the missing list. Missing accounts tagged `#autopay` are annotated.
3. **Monitored payees:** for each configured payee, looks for an outgoing payment within the
   same window (completed or scheduled).
4. Prints a two-section report; the bash wrapper optionally emails it and pings a healthcheck.

## Files

| File | Purpose |
|------|---------|
| `cc_payment_report.py` | Core library: all detection logic and report formatting |
| `run_report.py` | Thin wrapper that reads `config.py` and runs the report |
| `config_template.py` | Template for `config.py` (copy and fill in) |
| `cc_payment_check.sh` | Bash wrapper: runs report, emails via Mailgun, pings healthcheck |
| `cc_payment_check.config.template` | Template for the bash config (copy and fill in) |
| `requirements.txt` | Python dependencies (pinned actualpy version) |
| `CHANGELOG.md` | Version history |

## Customization

### Change the date window

In `generate_report()` (in `cc_payment_report.py`):

```python
# Change from ±2 weeks to ±1 month
start_date = today - timedelta(days=30)
end_date = today + timedelta(days=30)
```

### Change credit card detection

In `is_credit_card_account()`:

```python
return 'Credit Card' in account.name   # match by name instead of the 💳 prefix
```

## Technical Details

- **Date format:** Actual stores dates as integers in `YYYYMMDD` form (e.g. `20260106`).
- **Transfer detection:** a payment is a transaction whose payee has `transfer_acct` set.
- **Scheduled transactions:** stored as Rules with `date`/`amount`/`acct` conditions and a
  `link-schedule` action. Only future, non-zero schedules are considered.
- **Balance check:** accounts with `balance_current` of `None` (closed/inactive) or `0`
  (paid off) are excluded from the missing list.
- **Autopay detection:** reads `account.notes` defensively and looks for the `#autopay` tag.

## Requirements

- Python 3.7+
- actualpy (see `requirements.txt`)
- Access to an Actual Budget server
- Credit card accounts named with a `💳` prefix
- (Optional) Mailgun account + Healthchecks.io for scheduled email reports
- (Optional) A Linux host / Raspberry Pi for cron automation

## License

MIT

## Support

- actualpy documentation: https://actualpy.readthedocs.io/
- Actual Budget: https://actualbudget.org/
