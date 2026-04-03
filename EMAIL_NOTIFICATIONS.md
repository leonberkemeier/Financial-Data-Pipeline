# Email Notification System

The Financial Data Aggregator now includes automatic email notifications that alert you when each pipeline completes successfully or fails.

## 🚀 Setup

### 1. Get Gmail App Password

For Gmail, you need to create an **App-Specific Password** (not your regular password):

1. Visit: https://myaccount.google.com/apppasswords
2. Select **App**: Mail
3. Select **Device**: Windows Computer (or your device)
4. Click **Generate**
5. Copy the 16-character password provided

### 2. Configure Environment Variables

Update your `.env` file with your email credentials:

```env
# Email Notification Settings
SENDER_EMAIL=stockscreener62@gmail.com
SENDER_PASSWORD=your_app_password_here
RECIPIENT_EMAIL=leonberkemeier@gmail.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Email Notifications (true/false)
SEND_SUCCESS_EMAILS=true
SEND_FAILURE_EMAILS=true
```

### 3. Test Email Configuration

Create a test script `test_email.py`:

```python
#!/usr/bin/env python
import os
from dotenv import load_dotenv
from src.utils.email_notifier import EmailNotifier

load_dotenv()

notifier = EmailNotifier(
    sender_email=os.getenv('SENDER_EMAIL'),
    sender_password=os.getenv('SENDER_PASSWORD'),
    recipient_email=os.getenv('RECIPIENT_EMAIL'),
    smtp_server=os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
    smtp_port=int(os.getenv('SMTP_PORT', '587'))
)

# Test success email
print("Sending test success email...")
notifier.send_success_notification(
    pipeline_name="Test Pipeline",
    records_count=1000,
    execution_time=45.5,
    details={
        'Test Status': 'Working correctly',
        'Email Setup': 'Complete'
    }
)

print("\nTest complete! Check your inbox.")
```

Run it:

```bash
source venv/bin/activate
python test_email.py
```

## 📧 Email Notifications

### Success Email

When a pipeline completes successfully, you'll receive an email with:

- ✅ Pipeline name and status
- 📊 Number of records processed
- ⏱️ Execution time
- 📅 Timestamp
- 📋 Additional details (tickers, symbols, indicators, etc.)

**Example Success Email:**
```
Subject: ✅ Crypto Pipeline - SUCCESS

Pipeline Name: Crypto
Records Processed: 465
Execution Time: 8m 32s
Timestamp: 2026-01-02 21:36:04
Additional Details:
  Cryptocurrencies: BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, MATIC, LINK, UNI, USDT, USDC, ARB, OP
  Days of Data: 30
  Rate Limit Delay: 20.0s
```

### Failure Email

When a pipeline fails, you'll receive an email with:

- ❌ Pipeline name and status
- 🔴 Error message
- ⏱️ How long the pipeline ran before failing
- 📅 Timestamp
- 📋 Additional details if available

**Example Failure Email:**
```
Subject: ❌ Economic Indicators Pipeline - FAILED

Pipeline Name: Economic Indicators
Error Message: [Specific error message]
Execution Time Before Failure: 2m 15s
Timestamp: 2026-01-02 15:23:45
```

## 🛠️ Customization

### Disable Specific Email Types

Edit `.env`:

```env
# Only get success emails
SEND_SUCCESS_EMAILS=true
SEND_FAILURE_EMAILS=false

# Only get failure alerts
SEND_SUCCESS_EMAILS=false
SEND_FAILURE_EMAILS=true

# Disable all emails
SEND_SUCCESS_EMAILS=false
SEND_FAILURE_EMAILS=false
```

### Change Recipient Email

To send notifications to multiple people, create a helper function. Edit your pipeline runner:

```python
# For multiple recipients, modify email_notifier.py
# Currently sends to: RECIPIENT_EMAIL

# Future enhancement: support comma-separated list
RECIPIENT_EMAIL=email1@gmail.com,email2@gmail.com
```

## 🔍 Troubleshooting

### "Failed to authenticate with SMTP server"

- Verify you're using an **App-Specific Password**, not your regular Gmail password
- Ensure **2-Step Verification** is enabled in Google Account
- Make sure `SENDER_EMAIL` and `SENDER_PASSWORD` match exactly

### "Email credentials not configured"

Missing one or more required environment variables:
- `SENDER_EMAIL`
- `SENDER_PASSWORD`
- `RECIPIENT_EMAIL`

Check your `.env` file and verify all three are set.

### Email not received

1. Check Gmail spam folder
2. Verify email address is correct in `RECIPIENT_EMAIL`
3. Test with `test_email.py` script
4. Check logs for error messages: `tail -f /var/log/financial-data/*.log | grep -i email`

### SMTP Connection Error

- Ensure `SMTP_SERVER` is `smtp.gmail.com`
- Verify `SMTP_PORT` is `587` (uses TLS, not port 25 or 465)
- Check your firewall allows outbound connections to port 587

## 📜 Email Notification Code

The notification system is implemented in `src/utils/email_notifier.py`:

- **`EmailNotifier` class**: Main notification service
- **`send_success_notification()`**: Send success emails
- **`send_failure_notification()`**: Send failure emails
- **`_send_email()`**: Low-level SMTP communication

Usage in pipelines:

```python
# Initialize
notifier = EmailNotifier(
    sender_email="sender@gmail.com",
    sender_password="app_password",
    recipient_email="recipient@gmail.com",
    smtp_server="smtp.gmail.com",
    smtp_port=587
)

# Send success
notifier.send_success_notification(
    pipeline_name="Crypto",
    records_count=465,
    execution_time=512.4,
    details={'Cryptocurrencies': 'BTC, ETH, ...'}
)

# Send failure
notifier.send_failure_notification(
    pipeline_name="Crypto",
    error_message="API rate limit exceeded",
    execution_time=45.2
)
```

## 📦 Dependencies

Email functionality uses only built-in Python libraries:
- `smtplib` - SMTP client
- `email.mime` - Email message formatting

No additional packages required beyond existing `requirements.txt`.

## 🔐 Security Notes

- **Never commit `.env` file** to version control - it contains passwords
- **Use App-Specific Passwords** with Gmail, not your main password
- The `.env` file should have restrictive permissions:

```bash
chmod 600 .env
```

- Passwords are only used for SMTP authentication, never stored or logged
