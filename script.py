import requests
import html
import socket
import os
import sys
import smtplib
from email.message import EmailMessage

# Configuration Constants
URL = "https://android.googleapis.com/attestation/root"
SNAPSHOT_FILE = "last_snapshot.txt"
FETCH_CURRENT_CERTS_TIMEOUT_IN_SEC = 60
SMTP_SERVER_TIMEOUT_IN_SEC = 60

# Email Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

def fetch_current_certs(url):
    response = requests.get(url, timeout=FETCH_CURRENT_CERTS_TIMEOUT_IN_SEC)
    response.raise_for_status()
    return response.text

def load_last_snapshot(file_path):
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def save_snapshot(file_path, content):
    if not content: return
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

def generate_html_report(old_content, new_content):
    safe_old = html.escape(old_content) if old_content else "No previous data"
    safe_new = html.escape(new_content)
    
    status_msg = "✅ No changes detected." if old_content == new_content else "⚠️ Changes detected in certificates!"
    color = "#28a745" if old_content == new_content else "#d9534f"

    report_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
        <h2 style="color: {color}; border-bottom: 2px solid {color}; padding-bottom: 10px;">
            Android Attestation Root Certs Report
        </h2>
        <p><strong>Status:</strong> {status_msg}</p>

        <h3 style="background-color: #f8f9fa; padding: 10px; border-left: 5px solid #6c757d;">Previous Data</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <tr>
                <td style="border: 1px solid #ddd; padding: 15px; background-color: #ffffff; font-family: 'Courier New', monospace; font-size: 13px; white-space: pre-wrap; word-break: break-all;">
                    {safe_old}
                </td>
            </tr>
        </table>

        <h3 style="background-color: #f8f9fa; padding: 10px; border-left: 5px solid #007bff;">New Data</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="border: 1px solid #ddd; padding: 15px; background-color: #ffffff; font-family: 'Courier New', monospace; font-size: 13px; white-space: pre-wrap; word-break: break-all;">
                    {safe_new}
                </td>
            </tr>
        </table>
        
        <p style="font-size: 11px; color: #888; margin-top: 20px;">Automated Monitoring System</p>
    </body>
    </html>
    """
    return report_html

class EmailStatus:
    SUCCESS_TYPE = "SUCCESS"
    FAILED_TYPE = "FAILED"
    TIMEOUT_TYPE = "TIMEOUT"
    MISSING_TYPE = "MISSING_CREDENTIALS"

    def __init__(self, type, message=""):
        self.type = type
        self.message = message
    def is_failure(self): return self.type != EmailStatus.SUCCESS_TYPE
    def __str__(self): return self.message

def send_email_report(report_html):
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        return EmailStatus(EmailStatus.MISSING_TYPE, "Failed: Email credentials missing.")
    
    msg = EmailMessage()
    msg['Subject'] = "Android Attestation Root Certs Report"
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['X-Priority'] = '1 (Highest)'
    msg['Importance'] = 'High'

    msg.set_content("Please use an HTML compatible email client.") # Plain text fallback
    msg.add_alternative(report_html, subtype='html')

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=SMTP_SERVER_TIMEOUT_IN_SEC)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return EmailStatus(EmailStatus.SUCCESS_TYPE, "Email sent successfully.")
    except (socket.timeout, TimeoutError):
        return EmailStatus(EmailStatus.TIMEOUT_TYPE, "Failed: Connection timed out.")
    except Exception as e:
        return EmailStatus(EmailStatus.FAILED_TYPE, f"Failed: {str(e)}")

def main():
    try:
        current_data = fetch_current_certs(URL)
        last_data = load_last_snapshot(SNAPSHOT_FILE)
        
        report = generate_html_report(last_data, current_data)
        
        if last_data != current_data:
            save_snapshot(SNAPSHOT_FILE, current_data)
            print("Snapshot updated due to changes or initial run.")

        status = send_email_report(report)
        print(status)
        
        if status.is_failure():
            sys.exit(1)
            
    except Exception as e:
        error_html = f"<h3>Critical Error</h3><p>{html.escape(str(e))}</p>"
        send_email_report(error_html)
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
