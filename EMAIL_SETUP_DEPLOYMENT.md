# Email Notification Setup Guide

This guide covers setting up email notifications before deploying to your production server.

## Quick Setup (5 minutes)

### Step 1: Get Gmail App Password

1. Visit: **https://myaccount.google.com/apppasswords**
2. You might see "App passwords" or be prompted to enable 2-Step Verification first
3. If prompted for 2-Step Verification:
   - Go to https://myaccount.google.com/security
   - Enable "2-Step Verification"
   - Then return to App passwords
4. Select:
   - **App**: Mail
   - **Device**: Windows Computer (or your device type)
5. Click **Generate**
6. Google will show you a 16-character password like: `abcd efgh ijkl mnop`
7. **Copy this password** (excluding spaces)

### Step 2: Create `.env` File Locally

Before deploying, test locally:

```bash
cd /home/archy/Desktop/Server/FinancialData/financial_data_aggregator

# Copy example env file
cp .env.example .env

# Edit with your credentials
nano .env
```

Set these values:

```env
SENDER_EMAIL=stockscreener62@gmail.com
SENDER_PASSWORD=abcdefghijklmnop
RECIPIENT_EMAIL=leonberkemeier@gmail.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SEND_SUCCESS_EMAILS=true
SEND_FAILURE_EMAILS=true
```

### Step 3: Test Email System Locally

```bash
source venv/bin/activate
python test_email_notifications.py
```

Expected output:
```
======================================================================
EMAIL NOTIFICATION SYSTEM - TEST
======================================================================

📧 Checking email configuration...
  Sender Email: stockscreener62@gmail.com
  Recipient Email: leonberkemeier@gmail.com
  SMTP Server: smtp.gmail.com:587

✅ Configuration found

🔌 Initializing email notifier...
✅ Email notifier initialized

📤 Sending test SUCCESS email...
✅ Success email sent! (email sent successfully to leonberkemeier@gmail.com)

📤 Sending test FAILURE email...
✅ Failure email sent! (email sent successfully to leonberkemeier@gmail.com)

======================================================================
✅ EMAIL SYSTEM TEST SUCCESSFUL!
======================================================================

Check your inbox: You should have received 2 test emails
💡 The email notification system is ready for production use!
```

### Step 4: Check Your Email

- Go to: **leonberkemeier@gmail.com**
- You should have 2 test emails:
  - ✅ Email System Test - SUCCESS (with green styling)
  - ❌ Email System Test - FAILED (with red styling)

If emails don't appear:
1. Check **Spam/Promotions** folder
2. Re-run test: `python test_email_notifications.py`
3. Check logs for errors (see Troubleshooting below)

---

## Deployment to Server

### Step 1: Copy `.env` to Server

After testing locally and confirming emails work:

```bash
# From your local machine
scp .env user@your-server:/opt/financial-data/.env

# Verify file exists on server
ssh user@your-server "ls -la /opt/financial-data/.env"
```

### Step 2: Restrict `.env` Permissions

On the server, ensure only your user can read the `.env` file:

```bash
ssh user@your-server
cd /opt/financial-data
chmod 600 .env
ls -la .env  # Should show: -rw------- 1 user user
```

### Step 3: Test on Server

```bash
ssh user@your-server
cd /opt/financial-data
source venv/bin/activate
python test_email_notifications.py
```

Should get the same success output as local testing.

### Step 4: Run Pipelines with Email Notifications

Now when you run the pipelines, emails will be sent automatically:

```bash
python unified_pipeline.py --all
```

You'll receive emails for each pipeline:
- ✅ Crypto Pipeline - SUCCESS
- ✅ Stocks Pipeline - SUCCESS
- ✅ Bonds Pipeline - SUCCESS
- ✅ Economic Indicators Pipeline - SUCCESS
- ✅ Commodities Pipeline - SUCCESS

If any pipeline fails:
- ❌ [Pipeline Name] Pipeline - FAILED (with error details)

---

## Cron Job Integration

Your cron jobs (from deployment guide) will automatically send emails:

```bash
# These cron jobs send emails on success/failure
0 1 * * * cd /opt/financial-data && source venv/bin/activate && python unified_pipeline.py --crypto >> /var/log/financial-data/crypto.log 2>&1

0 18 * * * cd /opt/financial-data && source venv/bin/activate && python unified_pipeline.py --stocks >> /var/log/financial-data/stocks.log 2>&1

0 15 * * * cd /opt/financial-data && source venv/bin/activate && python unified_pipeline.py --bonds --economic >> /var/log/financial-data/bonds_econ.log 2>&1

0 17 * * * cd /opt/financial-data && source venv/bin/activate && python unified_pipeline.py --commodities >> /var/log/financial-data/commodities.log 2>&1
```

Each day at the scheduled times, you'll receive notifications about pipeline success or failure.

---

## Troubleshooting

### Email Not Received

**Check 1: Email credentials are correct**
```bash
# Verify .env file
cat .env | grep EMAIL
```

Should show:
```
SENDER_EMAIL=stockscreener62@gmail.com
SENDER_PASSWORD=abcdefghijklmnop
RECIPIENT_EMAIL=leonberkemeier@gmail.com
```

**Check 2: Gmail App Password format**
- Must be 16 characters (without spaces)
- Generated from: https://myaccount.google.com/apppasswords
- NOT your regular Gmail password

**Check 3: Run test script**
```bash
python test_email_notifications.py
```

If test fails, check for error messages in output.

**Check 4: Check spam folder**
- Emails might end up in Gmail's Spam or Promotions folder
- Whitelist `stockscreener62@gmail.com` if needed

### "Failed to authenticate with SMTP server"

This means the `SENDER_PASSWORD` is incorrect:

1. Go back to https://myaccount.google.com/apppasswords
2. Generate a NEW App Password (old one might have expired)
3. Update `.env` with the new password
4. Save and test: `python test_email_notifications.py`

### "Email credentials not configured"

One of the required environment variables is missing in `.env`:
- `SENDER_EMAIL` - must be set
- `SENDER_PASSWORD` - must be set
- `RECIPIENT_EMAIL` - must be set

Run: `cat .env | grep -E "(SENDER_EMAIL|SENDER_PASSWORD|RECIPIENT_EMAIL)"` to verify all three are present.

### Pipeline runs but no email received

Check if email notifications are enabled in `.env`:

```bash
cat .env | grep SEND_
```

Should show:
```
SEND_SUCCESS_EMAILS=true
SEND_FAILURE_EMAILS=true
```

If either is `false`, emails won't be sent for that type (success or failure).

### View Email Debug Logs

Check the pipeline logs for email-related messages:

```bash
# On server
tail -50 /var/log/financial-data/crypto.log | grep -i email
tail -50 /var/log/financial-data/stocks.log | grep -i email
tail -50 /var/log/financial-data/bonds_econ.log | grep -i email
tail -50 /var/log/financial-data/commodities.log | grep -i email

# Successful send shows: ✉️ Email sent successfully to leonberkemeier@gmail.com
# Errors show: ERROR | ... | email_notifier:...
```

---

## What Emails Look Like

### Success Email Example

**Subject:** ✅ Crypto Pipeline - SUCCESS

```
Pipeline Name: Crypto
Records Processed: 465
Execution Time: 8m 32s
Timestamp: 2026-01-02 21:36:04

Additional Details:
  Cryptocurrencies: BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOT, MATIC, LINK, UNI, USDT, USDC, ARB, OP
  Days of Data: 30
  Rate Limit Delay: 20.0s

Data is now available in the database and dashboard.
```

### Failure Email Example

**Subject:** ❌ Stocks Pipeline - FAILED

```
Pipeline Name: Stocks
Error Message: [Detailed error message]
Execution Time Before Failure: 5m 15s
Timestamp: 2026-01-02 18:42:30

Action Required: Please check the logs for more details.
```

---

## Next Steps

1. ✅ Test email locally with `test_email_notifications.py`
2. ✅ Verify emails arrive in your inbox
3. ✅ Deploy to server and copy `.env`
4. ✅ Test on server with `test_email_notifications.py`
5. ✅ Set up cron jobs (they'll send emails automatically)
6. ✅ Monitor your inbox for pipeline notifications

You're all set! You'll now receive automatic email notifications whenever your financial data pipelines run.
