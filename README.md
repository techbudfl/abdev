# Credit Card Payment Report v1.0

A Python tool to check if your credit card accounts have received payments within a 4-week window (±2 weeks from today).

## Version History

**v1.0** - Initial working version
- ✅ Detects transfers via Payees table (`transfer_acct` field)
- ✅ Handles Actual's integer date format (YYYYMMDD)
- ✅ One-line output for payments found
- ✅ Excludes zero-balance and None-balance accounts from missing payments

## Installation

```bash
pip install actualpy
```

## Quick Start

1. Edit the `config` dictionary in `cc_payment_report.py`:

```python
config = {
    'base_url': 'http://localhost:5006',  # Your Actual server URL
    'password': 'your_password',           # Server password
    'file': 'My Budget',                   # Budget file name or ID
}
```

2. Run:

```bash
python cc_payment_report.py
```

## Output Example

```
🔍 Checking for payments between 2026-01-21 and 2026-02-18
📅 Report run date: 2026-02-04

💳 Found 21 credit card accounts

================================================================================
CREDIT CARD PAYMENT REPORT
================================================================================

⚠️  MISSING PAYMENTS (No payment found in date range)
--------------------------------------------------------------------------------
  • 💳Amex Blue Cash
  • 💳 BofA Flex

✅ PAYMENTS FOUND
--------------------------------------------------------------------------------
  • 💳 Chase United | 2026-01-06 | $163.03 | 7027
  • 💳 Capital One  | 2026-01-05 | $7,016.80 | 
```

## How It Works

1. Connects to your Actual Budget server
2. Finds all accounts with names starting with `💳`
3. Looks for transactions in each account within ±2 weeks
4. Identifies payments by checking if the transaction's payee has a `transfer_acct` field
5. Reports:
   - Missing payments (only for accounts with non-zero balances)
   - Successful payments with date, amount, and notes on one line

## Files Included

- `cc_payment_report.py` - Main script
- `config_template.py` - Configuration template
- `README.md` - This file

## Requirements

- Python 3.7+
- actualpy library
- Access to an Actual Budget server
- Credit card accounts named with `💳` prefix

## Customization

### Change Date Range

Edit the `generate_report()` function:

```python
# Change from ±2 weeks to ±1 month
start_date = today - timedelta(days=30)
end_date = today + timedelta(days=30)
```

### Change Account Detection

Edit the `is_credit_card_account()` function:

```python
# Match by different criteria
return 'Credit Card' in account.name
```

## Technical Details

**Date Format**: Actual Budget stores dates as integers in YYYYMMDD format (e.g., 20260106)

**Transfer Detection**: Transfers are identified by checking if a transaction's payee has a `transfer_acct` field set in the Payees table

**Balance Check**: Excludes accounts from "missing payments" if:
- `balance_current is None` (inactive/closed accounts)
- `balance_current == 0` (paid off accounts)

## License

MIT

## Support

For issues or questions, refer to:
- actualpy documentation: https://actualpy.readthedocs.io/
- Actual Budget: https://actualbudget.org/