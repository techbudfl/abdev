#!/usr/bin/env python3
from cc_payment_report import generate_report, print_report
from config import *

# v3.0: Now passes monitored_payees from config
results = generate_report(
    base_url=BASE_URL,
    password=PASSWORD,
    file=FILE,
    monitored_payees=MONITORED_PAYEES if 'MONITORED_PAYEES' in dir() else [],
    encryption_password=ENCRYPTION_PASSWORD,
    data_dir=DATA_DIR,
    cert=CERT
)

print_report(results)
