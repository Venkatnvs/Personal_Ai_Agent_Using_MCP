from dataclasses import dataclass
from email.mime.application import MIMEApplication
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Email Tool")

@dataclass
class EmailInput:
    """
    Parameters required to send an email.
    Provide recipient email address, subject, and body content.
    """
    to: str
    subject: str
    body: str

@mcp.tool()
def send_email(to: str, subject: str, body: str, is_html: bool = False):
    """
    Send a plain text email using secure SMTP authentication.
    Supports multiple providers with error handling and delivery confirmation.
    
    Args:
        to: The recipient's email address
        subject: The email subject line
        body: The email body content (plain text)
    """
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")

    logging.info(f"Attempting to send email to {to}")
    try:
        msg = MIMEMultipart()
        msg['From'] = username
        msg['To'] = to
        msg['Subject'] = subject
        if is_html:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(username, password)
        server.sendmail(username, to, msg.as_string())
        server.quit()

        logging.info(f"Email successfully sent to {to}")
        return {"status": "success", "message": f"Email sent to {to} with subject '{subject}'."}
    except smtplib.SMTPAuthenticationError as e:
        logging.error(f"SMTP Authentication failed: {e}")
        return {"status": "error", "message": "Email authentication failed. Check credentials."}
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        return {"status": "error", "message": f"Failed to send email: {e}"}
    
@mcp.tool()
def send_email_with_attachment(to: str, subject: str, body: str, is_html: bool = False, attachment_path: str = None):
    """
    Send an email with an attachment.
    """
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")

    logging.info(f"Attempting to send email to {to}")
    try:
        msg = MIMEMultipart()
        msg['From'] = username
        msg['To'] = to
        msg['Subject'] = subject
        if is_html:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))
        
        with open(attachment_path, 'rb') as attachment:
            part = MIMEApplication(attachment.read(), Name=os.path.basename(attachment_path))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
            msg.attach(part)
            
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(username, password)
        server.sendmail(username, to, msg.as_string())
        server.quit()
        
        logging.info(f"Email successfully sent to {to}")
        return {"status": "success", "message": f"Email sent to {to} with subject '{subject}'."}
    except Exception as e:
        logging.error(f"Failed to send email: {e}")
        return {"status": "error", "message": f"Failed to send email: {e}"}

if __name__ == "__main__":
    mcp.run(transport='stdio')
