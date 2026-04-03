"""Email notification service for pipeline completion."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from loguru import logger
from typing import Optional, Dict


class EmailNotifier:
    """Send email notifications for pipeline runs."""

    def __init__(
        self,
        sender_email: str,
        sender_password: str,
        recipient_email: str,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587,
    ):
        """
        Initialize email notifier.

        Args:
            sender_email: Email address to send from
            sender_password: App-specific password or SMTP password
            recipient_email: Email address to send to
            smtp_server: SMTP server address (default: Gmail)
            smtp_port: SMTP port (default: 587 for TLS)
        """
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_email = recipient_email
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

    def send_success_notification(
        self,
        pipeline_name: str,
        records_count: int,
        execution_time: float,
        details: Optional[Dict] = None,
    ) -> bool:
        """
        Send success notification email.

        Args:
            pipeline_name: Name of the pipeline (e.g., "Crypto", "Stocks")
            records_count: Number of records processed
            execution_time: Time taken in seconds
            details: Optional dict with additional details

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            subject = f"✅ {pipeline_name} Pipeline - SUCCESS"

            # Format execution time
            minutes = int(execution_time // 60)
            seconds = int(execution_time % 60)
            time_str = (
                f"{minutes}m {seconds}s"
                if minutes > 0
                else f"{seconds}s"
            )

            # Build email body
            body = f"""
<html>
  <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
      
      <h2 style="color: #27ae60; margin-top: 0;">✅ Pipeline Execution Successful</h2>
      
      <div style="background-color: #d4edda; border-left: 4px solid #27ae60; padding: 15px; margin: 20px 0;">
        <p style="margin: 0; color: #155724;">
          <strong>{pipeline_name} Pipeline</strong> completed successfully!
        </p>
      </div>

      <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
        <tr style="background-color: #f8f9fa;">
          <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Pipeline Name:</td>
          <td style="padding: 10px; border: 1px solid #ddd;">{pipeline_name}</td>
        </tr>
        <tr>
          <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Records Processed:</td>
          <td style="padding: 10px; border: 1px solid #ddd;">{records_count:,}</td>
        </tr>
        <tr style="background-color: #f8f9fa;">
          <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Execution Time:</td>
          <td style="padding: 10px; border: 1px solid #ddd;">{time_str}</td>
        </tr>
        <tr>
          <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Timestamp:</td>
          <td style="padding: 10px; border: 1px solid #ddd;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
        </tr>
"""

            if details:
                body += f"""
        <tr style="background-color: #f8f9fa;">
          <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Additional Details:</td>
          <td style="padding: 10px; border: 1px solid #ddd;">
"""
                for key, value in details.items():
                    body += f"<div><strong>{key}:</strong> {value}</div>\n"
                body += """
          </td>
        </tr>
"""

            body += """
      </table>

      <div style="background-color: #e7f3ff; border-left: 4px solid #2196F3; padding: 15px; margin: 20px 0;">
        <p style="margin: 0; color: #1565c0; font-size: 14px;">
          Data is now available in the database and dashboard.
        </p>
      </div>

      <footer style="border-top: 1px solid #ddd; margin-top: 20px; padding-top: 15px; font-size: 12px; color: #666;">
        <p>Financial Data Aggregator | Automated Pipeline Notification</p>
      </footer>

    </div>
  </body>
</html>
"""

            return self._send_email(subject, body)

        except Exception as e:
            logger.error(f"Error preparing success notification: {str(e)}")
            return False

    def send_failure_notification(
        self,
        pipeline_name: str,
        error_message: str,
        execution_time: Optional[float] = None,
        details: Optional[Dict] = None,
    ) -> bool:
        """
        Send failure notification email.

        Args:
            pipeline_name: Name of the pipeline
            error_message: Error message/description
            execution_time: Optional time taken before failure
            details: Optional dict with additional details

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            subject = f"❌ {pipeline_name} Pipeline - FAILED"

            time_str = ""
            if execution_time:
                minutes = int(execution_time // 60)
                seconds = int(execution_time % 60)
                time_str = (
                    f"{minutes}m {seconds}s"
                    if minutes > 0
                    else f"{seconds}s"
                )

            body = f"""
<html>
  <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
      
      <h2 style="color: #c0392b; margin-top: 0;">❌ Pipeline Execution Failed</h2>
      
      <div style="background-color: #f8d7da; border-left: 4px solid #c0392b; padding: 15px; margin: 20px 0;">
        <p style="margin: 0; color: #721c24;">
          <strong>{pipeline_name} Pipeline</strong> encountered an error and did not complete successfully.
        </p>
      </div>

      <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
        <tr style="background-color: #f8f9fa;">
          <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Pipeline Name:</td>
          <td style="padding: 10px; border: 1px solid #ddd;">{pipeline_name}</td>
        </tr>
        <tr>
          <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Error Message:</td>
          <td style="padding: 10px; border: 1px solid #ddd; color: #c0392b;">
            <code style="background-color: #ffe6e6; padding: 5px; border-radius: 3px; font-size: 12px;">
              {error_message}
            </code>
          </td>
        </tr>
"""

            if time_str:
                body += f"""
        <tr style="background-color: #f8f9fa;">
          <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Execution Time Before Failure:</td>
          <td style="padding: 10px; border: 1px solid #ddd;">{time_str}</td>
        </tr>
"""

            body += f"""
        <tr>
          <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Timestamp:</td>
          <td style="padding: 10px; border: 1px solid #ddd;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
        </tr>
"""

            if details:
                body += f"""
        <tr style="background-color: #f8f9fa;">
          <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Additional Details:</td>
          <td style="padding: 10px; border: 1px solid #ddd;">
"""
                for key, value in details.items():
                    body += f"<div><strong>{key}:</strong> {value}</div>\n"
                body += """
          </td>
        </tr>
"""

            body += """
      </table>

      <div style="background-color: #fff3cd; border-left: 4px solid #ff9800; padding: 15px; margin: 20px 0;">
        <p style="margin: 0; color: #856404; font-size: 14px;">
          <strong>Action Required:</strong> Please check the logs for more details.
        </p>
      </div>

      <footer style="border-top: 1px solid #ddd; margin-top: 20px; padding-top: 15px; font-size: 12px; color: #666;">
        <p>Financial Data Aggregator | Automated Pipeline Notification</p>
      </footer>

    </div>
  </body>
</html>
"""

            return self._send_email(subject, body)

        except Exception as e:
            logger.error(f"Error preparing failure notification: {str(e)}")
            return False

    def _send_email(self, subject: str, body: str) -> bool:
        """
        Send email via SMTP.

        Args:
            subject: Email subject
            body: Email body (HTML)

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = self.recipient_email

            # Attach HTML body
            part = MIMEText(body, "html")
            message.attach(part)

            # Connect to SMTP server and send
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(
                    self.sender_email, self.recipient_email, message.as_string()
                )

            logger.info(f"✉️  Email sent successfully to {self.recipient_email}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error(
                "Failed to authenticate with SMTP server. Check credentials."
            )
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error occurred: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
