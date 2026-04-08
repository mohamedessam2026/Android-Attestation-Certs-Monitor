import requests
import difflib
import os
import smtplib
from email.message import EmailMessage

# Configuration Constants
URL = "https://android.googleapis.com/attestation/root"
SNAPSHOT_FILE = "last_snapshot.txt"

# Email Configuration
SMTP_SERVER = "smtp.gmail.com"  # Change this if your company uses a different server , example : smtp.office365.com
SMTP_PORT = 587                 # Standard port for TLS
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

# Fetches the raw certificate data from the specified URL.
def fetch_current_certs(url):
    response = requests.get(url)
    response.raise_for_status()  # Raises an exception for HTTP errors (4xx or 5xx)
    return response.text

# Reads the content of the last saved snapshot from the local disk.
# Returns None if the file does not exist.
def load_last_snapshot(file_path):
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

# Saves the current content to a local file for future comparisons.
def save_snapshot(file_path, content):
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

# Compares old and new content.
# Returns a formatted string showing the differences or a 'No changes' message.
def generate_diff_report(old_content, new_content):
    if old_content == new_content:
        return "Status: No changes. The content matches the last month's snapshot."
    
    # Generate a unified diff for a clear, line-by-line comparison report
    diff = difflib.unified_diff(
        old_content.splitlines(),
        new_content.splitlines(),
        fromfile='Last_Month_Snapshot',
        tofile='Current_Web_Data',
        lineterm=''
    )
    
    diff_text = "\n".join(list(diff))
    return f"ALERT: Changes detected!\n\nDetailed Report:\n{diff_text}"

def display_report(report_text):
    print("\n" + "="*50)
    print(report_text)
    print("="*50 + "\n")

# Sends the report via SMTP.
def send_email_report(report_text):
    msg = EmailMessage()
    msg.set_content(report_text)
    msg['Subject'] = "Android Attestation Root Certs Report"
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL

    # set mail as a high Priority 
    msg['X-Priority'] = '1 (Highest)'
    msg['Importance'] = 'High'

    try:
        # 1. Establish a standard connection
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.set_debuglevel(0) # Set to 1 if you want to see the full communication log
        
        # 2. Identify ourselves to the server
        server.ehlo()
        
        # 3. Upgrade the connection to secure TLS
        server.starttls()
        
        # 4. Re-identify ourselves as a secure connection
        server.ehlo()
        
        # 5. Login and send
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        
        # 6. Close connection gracefully
        server.quit()
        return "Email sent successfully via TLS."
    except Exception as e:
        return f"Failed to send email: {str(e)}"


def main():
    try:
        # Step 1: Fetch live data
        current_data = fetch_current_certs(URL)
        
        # Step 2: Load previous state
        last_data = load_last_snapshot(SNAPSHOT_FILE)
        
        # Step 3: Handle first-run or comparison
        if last_data is None:
            save_snapshot(SNAPSHOT_FILE, current_data)
            report = "Action: No previous snapshot found. Initial data has been saved."
        else:
            report = generate_diff_report(last_data, current_data)
            if "ALERT" in report:
                save_snapshot(SNAPSHOT_FILE, current_data)

        # Step 4: Display to console
        display_report(report)

        # Step 5: Send Email (Regardless of outcome as requested)
        print("Sending email report...")
        email_status = send_email_report(report)
        print(email_status)

    except Exception as e:
        error_message = f"Critical Error: {e}"
        display_report(error_message)

        # Send error as a report too
        send_email_report(error_message) 

if __name__ == "__main__":
    main()