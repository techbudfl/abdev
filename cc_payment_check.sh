#!/bin/bash

# Get the directory where this script is located
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source the configuration file
CONFIG_FILE="${SCRIPT_PATH}/cc_payment_check.config"

if [ ! -f "$CONFIG_FILE" ]; then
  echo "Error: Configuration file not found: $CONFIG_FILE"
  echo "Please copy cc_payment_check.config.template to cc_payment_check.config and configure it."
  exit 1
fi

source "$CONFIG_FILE"

# Activate virtual environment
source "$VENV_PATH"

# Change to script directory
cd "$SCRIPT_PATH"

# Initialize exit code
REPORT_EXIT=0

# Run the credit card payment report and capture output
echo "Running Credit Card Payment Report - $(date)" > "$REPORT_OUTPUT"
echo "===============================================================================" >> "$REPORT_OUTPUT"
echo "" >> "$REPORT_OUTPUT"

python -W ignore::UserWarning run_report.py >> "$REPORT_OUTPUT" 2>&1 || REPORT_EXIT=$?

echo "" >> "$REPORT_OUTPUT"
echo "===============================================================================" >> "$REPORT_OUTPUT"
echo "Report completed at: $(date)" >> "$REPORT_OUTPUT"

# Prepare email subject based on success/failure
if [ $REPORT_EXIT -eq 0 ]; then
  EMAIL_SUBJECT="✅ Credit Card Payment Report - $(date +%Y-%m-%d)"
else
  EMAIL_SUBJECT="❌ Credit Card Payment Report FAILED - $(date +%Y-%m-%d)"
fi

# NEW v3.1: Wrap the report in HTML with fixed-width font for better email rendering
HTML_CONTENT="<!DOCTYPE html>
<html>
<head>
  <meta charset=\"UTF-8\">
  <style>
    body {
      font-family: 'Courier New', Courier, monospace;
      font-size: 13px;
      line-height: 1.4;
      background-color: #1e1e1e;
      color: #d4d4d4;
      padding: 20px;
    }
    pre {
      font-family: 'Courier New', Courier, monospace;
      font-size: 13px;
      white-space: pre;
      margin: 0;
      background-color: #1e1e1e;
      color: #d4d4d4;
    }
  </style>
</head>
<body>
  <pre>$(cat $REPORT_OUTPUT)</pre>
</body>
</html>"

# Send email via Mailgun with HTML content
curl -s --user "api:${MAILGUN_API_KEY}" \
  "https://api.mailgun.net/v3/${MAILGUN_DOMAIN}/messages" \
  -F from="${EMAIL_FROM}" \
  -F to="${EMAIL_TO}" \
  -F subject="${EMAIL_SUBJECT}" \
  -F text="$(cat $REPORT_OUTPUT)" \
  -F html="${HTML_CONTENT}" \
  > /dev/null 2>&1

MAIL_EXIT=$?

# Send healthcheck ping
if [ $REPORT_EXIT -eq 0 ] && [ $MAIL_EXIT -eq 0 ]; then
  curl -fsS --retry 3 -m 10 "$HEALTHCHECK_URL" >/dev/null 2>&1  # Success ping
else
  curl -fsS --retry 3 -m 10 "$HEALTHCHECK_URL/fail" >/dev/null 2>&1  # Fail ping
fi

# Clean up temp file (optional - keep for debugging if needed)
# rm "$REPORT_OUTPUT"

# Output to console
cat "$REPORT_OUTPUT"
echo "==============================================================================="

exit $REPORT_EXIT
