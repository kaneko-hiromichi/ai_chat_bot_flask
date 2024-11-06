# app/services/email.py
import smtplib
from email.mime.text import MIMEText
from ..config import Config

class EmailService:
    @staticmethod
    def send_email(to_email, subject, content):
        msg = MIMEText(content)
        msg['Subject'] = subject
        msg['From'] = Config.MAIL_USERNAME
        msg['To'] = to_email

        try:
            server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT)
            server.starttls()
            server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
            print(f"Email sent successfully to: {to_email}")
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False

    @staticmethod
    def send_reset_password(to_email, reset_link):
        subject = "パスワードリセットリクエスト"
        content = f"パスワードリセットリンク: {reset_link}"
        return EmailService.send_email(to_email, subject, content)

    @staticmethod
    def send_unlock_notification(to_email, unlock_link):
        subject = "アカウントロック通知"
        content = f"アカウントがロックされました。解除するには次のリンクをクリックしてください: {unlock_link}"
        return EmailService.send_email(to_email, subject, content)