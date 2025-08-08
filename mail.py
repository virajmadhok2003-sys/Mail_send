import smtplib
import email
import os
from email.message import EmailMessage
from dotenv import load_dotenv
from pathlib import Path
import mimetypes


load_dotenv()
mail_id=os.getenv("MAIL_ID")
mail_password=os.getenv("MAIL_PASSWORD")

def send_main_mail(sender_email,message,attachments):
    try:
        print(attachments)
        print("hello")
        filename,filepath=attachments[0]
        print("hello1")
        print(filepath)
        msg = EmailMessage()
        msg["Subject"] = "Issue with your email attachment"
        msg["From"] = mail_id 
        msg["To"] = sender_email
        msg.set_content(message)
    #     for filename, filepath in attachments:
        if os.path.exists(filepath):
                with open(filepath, "rb") as f:
                    file_data = f.read()
                    ctype, encoding = mimetypes.guess_type(filename)
                    if ctype is None or encoding is not None:
                        # Default to generic binary data
                        maintype, subtype = 'application', 'octet-stream'
                    else:
                        maintype, subtype = ctype.split('/', 1)

                    msg.add_attachment(file_data, maintype=maintype, subtype=subtype, filename=filename) 

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(mail_id, mail_password)
            smtp.send_message(msg)

        print(f"Sent reply to {sender_email}")
        return "done"
    except Exception as e:
        print(f"Failed to send email: {e}")
        return "failed"
