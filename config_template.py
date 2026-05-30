# Configuration Template for Credit Card Payment Report
# Copy this to config.py and fill in your actual values

# Your Actual Budget server URL
BASE_URL = "http://localhost:5006"

# Server password
PASSWORD = "your_password_here"

# Budget file (can be name, ID, or Sync ID)
FILE = "My Budget"

# Optional: Encryption password if your budget is encrypted
ENCRYPTION_PASSWORD = None  # or "your_encryption_password"

# Optional: Directory to store downloaded files
DATA_DIR = None  # or "/path/to/data/directory"

# SSL certificate verification:
#   True  = validate against system CAs (correct for a real cert, e.g. LetsEncrypt)
#   False = skip verification (use for self-signed certs)
#   "/path/to/cert.pem" = validate against a specific cert/CA bundle
# Note: do NOT use None here -- newer versions of actualpy raise a TypeError.
CERT = True

# NEW in v3.0: List of payees to monitor for payments
# Add payee names (or partial names) that you want to track
# The system will check if payments were made to these payees in the date range
MONITORED_PAYEES = [
    "Target",
    "Auto Financing"
]

# Autopay accounts (v3.2):
# There is no setting here for autopay. To mark a credit card account as being on
# autopay, add the tag "#autopay" to that account's Notes field inside Actual Budget.
# Accounts tagged this way will be annotated with "(autopay)" in the report when they
# would otherwise be flagged as missing a payment (useful when autopay is scheduled
# more than two weeks out).
