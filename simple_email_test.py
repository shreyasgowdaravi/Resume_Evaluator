import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

load_dotenv()

EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.office365.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM")

def test_email():
    try:
        print("Attempting to connect to SMTP server...")

        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_USER
        msg['Subject'] = "Email Test - Resume Evaluator"

        body = "This is a test email to verify Office 365 SMTP configuration is working."
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        print("Connected to SMTP server")

        server.starttls()
        print("TLS started")

        server.login(EMAIL_USER, EMAIL_PASSWORD)   # <- App Password
        print("Login successful")

        server.send_message(msg)
        server.quit()

        print("✅ SUCCESS: Email sent successfully!")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ AUTHENTICATION ERROR: {str(e)}")
        return False

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    print(f"Testing email configuration:")
    print(f"Host: {EMAIL_HOST}")
    print(f"Port: {EMAIL_PORT}")
    print(f"User: {EMAIL_USER}")
    print(f"From: {EMAIL_FROM}")
    print("-" * 50)
    test_email()
