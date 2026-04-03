#!/usr/bin/env python
"""Test email notification system."""
import os
import sys
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from src.utils.email_notifier import EmailNotifier


def test_email_setup():
    """Test email configuration and send test emails."""
    
    logger.info("=" * 80)
    logger.info("EMAIL NOTIFICATION SYSTEM - TEST")
    logger.info("=" * 80)
    
    # Get credentials from environment
    sender_email = os.getenv('SENDER_EMAIL')
    sender_password = os.getenv('SENDER_PASSWORD')
    recipient_email = os.getenv('RECIPIENT_EMAIL')
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    
    logger.info("\n📧 Checking email configuration...")
    logger.info(f"  Sender Email: {sender_email}")
    logger.info(f"  Recipient Email: {recipient_email}")
    logger.info(f"  SMTP Server: {smtp_server}:{smtp_port}")
    
    # Validate configuration
    if not all([sender_email, sender_password, recipient_email]):
        logger.error("❌ Missing email configuration in .env file")
        logger.error("   Required: SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL")
        return False
    
    logger.info("✅ Configuration found\n")
    
    # Initialize notifier
    logger.info("🔌 Initializing email notifier...")
    try:
        notifier = EmailNotifier(
            sender_email=sender_email,
            sender_password=sender_password,
            recipient_email=recipient_email,
            smtp_server=smtp_server,
            smtp_port=smtp_port
        )
        logger.info("✅ Email notifier initialized\n")
    except Exception as e:
        logger.error(f"❌ Failed to initialize email notifier: {str(e)}")
        return False
    
    # Send test success email
    logger.info("📤 Sending test SUCCESS email...")
    try:
        success = notifier.send_success_notification(
            pipeline_name="Email System Test",
            records_count=1000,
            execution_time=45.75,
            details={
                'Test Type': 'Success Email Test',
                'Status': 'Email system is working correctly',
                'Configuration': 'Valid SMTP credentials'
            }
        )
        
        if success:
            logger.info("✅ Success email sent!\n")
        else:
            logger.error("❌ Failed to send success email\n")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error sending success email: {str(e)}\n")
        return False
    
    # Send test failure email
    logger.info("📤 Sending test FAILURE email...")
    try:
        success = notifier.send_failure_notification(
            pipeline_name="Email System Test",
            error_message="This is a test failure notification to verify the email system is working correctly.",
            execution_time=10.5
        )
        
        if success:
            logger.info("✅ Failure email sent!\n")
        else:
            logger.error("❌ Failed to send failure email\n")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error sending failure email: {str(e)}\n")
        return False
    
    # Success!
    logger.info("=" * 80)
    logger.info("✅ EMAIL SYSTEM TEST SUCCESSFUL!")
    logger.info("=" * 80)
    logger.info("\n📬 Check your inbox at: {recipient_email}")
    logger.info("   You should have received 2 test emails")
    logger.info("\n💡 The email notification system is ready for production use!")
    logger.info("   Emails will be sent automatically when pipelines complete.")
    
    return True


if __name__ == "__main__":
    success = test_email_setup()
    sys.exit(0 if success else 1)
