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

# Optional: SSL certificate path (or False to disable verification)
CERT = None  # or "/path/to/cert.pem" or False

# NEW in v3.0: List of payees to monitor for payments
# Add payee names (or partial names) that you want to track
# The system will check if payments were made to these payees in the date range
MONITORED_PAYEES = [
    "Target",
    "Auto Financing"
]
