import smtplib, ssl
import os 
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

sender_email = os.getenv("SENDER_EMAIL")
sender_password = os.getenv("SENDER_PASSWORD")

def send_email(receiver_email: str, subject: str, body: str) -> bool:
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject

    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()  # Secure the connection
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, message.as_string())
            server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error: {e}")

def main():
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")

    receiver_email = os.getenv("SENDER_EMAIL")

    context = ssl.create_default_context()

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = "Test Email from Python"

    body = "Hello, this is a test email sent from Python!"
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()  # Secure the connection
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, message.as_string())
            server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()