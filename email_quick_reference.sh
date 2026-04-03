#!/bin/bash
# Email Notification System - Quick Reference Card
# Copy this to your server for quick reference

echo "=========================================="
echo "EMAIL NOTIFICATION SYSTEM - QUICK GUIDE"
echo "=========================================="
echo ""

# Check if emails are configured
echo "1️⃣  VERIFY EMAIL CONFIGURATION"
echo "   Command: cat .env | grep EMAIL"
echo ""

# Test email system
echo "2️⃣  TEST EMAIL SYSTEM"
echo "   Command: python test_email_notifications.py"
echo "   Expected: Both success and failure emails sent"
echo ""

# View email-related logs
echo "3️⃣  CHECK EMAIL LOGS"
echo "   Command: tail -50 /var/log/financial-data/*.log | grep -i email"
echo "   Command: tail -50 /var/log/financial-data/crypto.log | grep -i '✉️'"
echo ""

# Common problems and solutions
echo "4️⃣  TROUBLESHOOTING"
echo ""
echo "Problem: Email not received"
echo "  → Check spam folder (Gmail's Promotions/Spam)"
echo "  → Run: python test_email_notifications.py"
echo "  → Verify .env has correct credentials"
echo ""

echo "Problem: Authentication failed"
echo "  → Go to: https://myaccount.google.com/apppasswords"
echo "  → Generate new App Password"
echo "  → Update SENDER_PASSWORD in .env"
echo "  → Re-run test: python test_email_notifications.py"
echo ""

echo "Problem: No 'Email sent successfully' log message"
echo "  → Email notifier not initialized (missing .env vars)"
echo "  → Check: grep 'email_notifier' /var/log/financial-data/*.log"
echo ""

echo "Problem: Emails disabled"
echo "  → Check: cat .env | grep SEND_"
echo "  → Should show: SEND_SUCCESS_EMAILS=true"
echo "  → Should show: SEND_FAILURE_EMAILS=true"
echo ""

# Enable/disable emails
echo "5️⃣  ENABLE/DISABLE EMAILS"
echo ""
echo "To disable success emails:"
echo "  sed -i 's/SEND_SUCCESS_EMAILS=.*/SEND_SUCCESS_EMAILS=false/' .env"
echo ""
echo "To disable failure emails:"
echo "  sed -i 's/SEND_FAILURE_EMAILS=.*/SEND_FAILURE_EMAILS=false/' .env"
echo ""
echo "To enable all emails:"
echo "  sed -i 's/SEND_SUCCESS_EMAILS=.*/SEND_SUCCESS_EMAILS=true/' .env"
echo "  sed -i 's/SEND_FAILURE_EMAILS=.*/SEND_FAILURE_EMAILS=true/' .env"
echo ""

# View recent emails in logs
echo "6️⃣  VIEW RECENT EMAIL ACTIVITY"
echo "   Command: grep -h '✉️\|Email sent successfully' /var/log/financial-data/*.log | tail -20"
echo ""

# Cron schedule
echo "7️⃣  DAILY EMAIL SCHEDULE"
echo "   01:00 AM → Crypto pipeline (emails sent)"
echo "   03:00 PM → Bonds + Economic pipelines (emails sent)"
echo "   05:00 PM → Commodities pipeline (emails sent)"
echo "   06:00 PM → Stocks pipeline (emails sent)"
echo ""

# Useful commands
echo "8️⃣  USEFUL COMMANDS"
echo ""
echo "Test email system:"
echo "  python test_email_notifications.py"
echo ""
echo "Check .env configuration:"
echo "  cat .env | grep -E '(SENDER|RECIPIENT|SMTP|SEND_)'"
echo ""
echo "Update recipient email:"
echo "  sed -i 's/RECIPIENT_EMAIL=.*/RECIPIENT_EMAIL=your-email@gmail.com/' .env"
echo ""
echo "View email-related log messages:"
echo "  grep -r 'email_notifier\|✉️' /var/log/financial-data/"
echo ""
echo "Count emails sent today:"
echo "  grep -h '✉️' /var/log/financial-data/*.log | wc -l"
echo ""
echo "View last 5 emails sent:"
echo "  grep -h '✉️' /var/log/financial-data/*.log | tail -5"
echo ""

echo "=========================================="
echo "For more info, see:"
echo "  • EMAIL_NOTIFICATIONS.md"
echo "  • EMAIL_SETUP_DEPLOYMENT.md"
echo "  • EMAIL_IMPLEMENTATION_SUMMARY.md"
echo "=========================================="
