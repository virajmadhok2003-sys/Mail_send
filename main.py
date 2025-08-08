import imaplib
import time
import email
import os
import fitz
from metadata import extract
import PyPDF2
from PyPDF2 import PdfReader
from email.utils import parseaddr
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from pathlib import Path
import shutil
import mimetypes

print("starting the execution")

mail_id=os.getenv("MAIL_ID")
mail_password=os.getenv("MAIL_PASSWORD")
IMAP_SERVER = "imap.gmail.com"
CHECK_INTERVAL = 10
SAVE_DIR = os.getenv("SAVE_DIR")
all_docs=os.path.join(SAVE_DIR,"all_docs")
valid_docs=os.path.join(SAVE_DIR,"valid_docs")
os.makedirs(all_docs, exist_ok=True)
os.makedirs(valid_docs,exist_ok=True)
filename=""
filepath=""
load_dotenv()

def get_all_uids():
    imap = imaplib.IMAP4_SSL(IMAP_SERVER)
    imap.login(mail_id, mail_password)
    imap.select("inbox")
    result, data = imap.uid('search', None, 'ALL')
    uids = data[0].split()
    imap.logout()
    return set(uids)





def fetch_email_by_uid(uid):
    imap = imaplib.IMAP4_SSL(IMAP_SERVER)
    imap.login(mail_id, mail_password)
    imap.select("inbox")
    result, data = imap.uid('fetch', uid, '(RFC822)')
    imap.logout()

    if result == 'OK':
        raw_email = data[0][1]
        # print(data)
        # print(raw_email)
        return email.message_from_bytes(raw_email)
    return None

def has_attachment(msg):
    attachments=[]
    not_valid=[]
    for part in msg.walk():
        content_disposition = str(part.get("Content-Disposition"))
        if content_disposition and "attachment" in content_disposition.lower():
            filename, filepath = save_and_convert_attachment(part)
            if filename:
                name,extension=os.path.splitext(filename)
                print("extension ",extension)
                if extension.lower()=='.pdf':
                    attachments.append((filename,filepath))
                elif extension.lower()!='.pdf':
                    print('The file is not exactly pdf')
                    not_valid.append((filename,filepath))
    #             else:
    #                 return True,filename,filepath,''
    #         return True, filename, filepath
    # return False, None, None,'doc'
    # if attachments:
    #     return True, attachments
    # if attachments:
    #     print("yes")
    #     print(attachments)
    #     return True, attachments
    # elif not_valid:
    #     print("no1")
    #     return False,''
    # else:
    #     print("no2")
    #     return False,'n/a'
    return attachments,not_valid
            

    # for part in msg.walk():
    #     # print("part ",part)
    #     content_disposition = str(part.get("Content-Disposition"))
    #     # if "attachment" in content_disposition.lower():
    #     if content_disposition and "attachment" in content_disposition.lower():
    #         filename = part.get_filename()
    #         if filename:
    #             # Get file extension
    #             name, extension = os.path.splitext(filename)
    #             save_and_convert_attachment(part)
    #             # print(f"Attachment found: {filename}")
    #             # print(f"Extension: {extension}")
    #         return True
    # return False


def save_and_convert_attachment(part):
    # print("save and convert")
    filename = part.get_filename()
    # filepath='N/A'
    # if  filename.lower().endswith(".pdf"):
    #     filepath = os.path.join(SAVE_DIR, filename)
    #     with open(filepath, "wb") as f:
    #         f.write(part.get_payload(decode=True))

    #     print(f"PDF saved to: {filepath}")
    filepath=os.path.join(all_docs,filename)
    
    with open(filepath,"wb") as f:
        f.write(part.get_payload(decode=True))
    
    return filename, filepath

def is_actual_pdf(file_path):
    try:
        with open(file_path, 'rb') as f:
            header = f.read(5)
            return header == b'%PDF-'
    except Exception as e:
        print(f"Error reading file: {e}")
        return False

def is_valid_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        _ = reader.pages[0]
        return True
    except Exception as e:
        print(f"Invalid PDF: {e}")
        return False
def is_really_a_pdf(file_path):
    return is_actual_pdf(file_path) and is_valid_pdf(file_path)

def send_mail(sender_email,message,attachments):
    try:
        msg = EmailMessage()
        msg["Subject"] = "Issue with your email attachment"
        msg["From"] = mail_id 
        msg["To"] = sender_email
        msg.set_content(message)
        for filename, filepath in attachments:
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
    
def validate(items,sender_email):
        name,path=items
        
        if is_really_a_pdf(path):
                    print("Hello World, there is an attachment and it is a pdf")
                    valid_pdf_path = os.path.join(valid_docs, name)
                    shutil.copy(path, valid_pdf_path)
                    extract(name,path,sender_email)
                
        else:
                    print('The pdf is not valid')
                    message="""Dear Sender, 
                                                The PDF file you uploaded is not a valid one. Kindly resend it.

    Regards"""
                    send_mail(sender_email,message,[items])
        


def start_monitoring():
    print("Monitoring inbox for new emails...")
    previous_uids = get_all_uids()
    while True:
        time.sleep(CHECK_INTERVAL)
        current_uids = get_all_uids()
        new_uids = current_uids - previous_uids

        if new_uids:
            for id in new_uids:
                print("Hello World - New email(s) received")
                msg=fetch_email_by_uid(id)
                if msg:
                    sender_email = parseaddr(msg.get("From"))[1]
                    attachments, not_valid= has_attachment(msg)

                    if attachments and not_valid:
                        for item in attachments:
                            validate(item,sender_email)
                            
                        for item in not_valid:
                            name,path=item
                            message="""Dear Sender, 
                                                You have not uploaded any pdf here.Kindly upload a pdf.  
                                                
        Regards"""
                            
                            send_mail(sender_email,message,[item])
                    elif attachments:
                        for item in attachments:
                         validate(item,sender_email)
                    elif not_valid:
                        message="""Dear Sender, 
                                                You have not uploaded any pdf here.Kindly upload a pdf.  
                                                
        Regards"""
                        for item in not_valid:
                            name,path=item
                            send_mail(sender_email,message,[item])
                    else:
                        message="""Dear Sender, 
                                                The mail you sent has no attachments. Kindly resend the mail with a proper attachment. 
                                    
        Regards"""
                        send_mail(sender_email,message,[])

        previous_uids = current_uids




#             print("ext ",ext)
#             if has_attach:
#                 for item in attachements:
#                     validate(item,sender_email)

# #                 if is_really_a_pdf(filepath):
# #                     print("Hello World, there is an attachment and it is a pdf")
# #                     extract(filename,filepath,sender_email)
# #                 else:
# #                     print('The pdf is not valid')
# #                     message="""Dear Sender, 
# #                                             The PDF file you uploaded is not a valid one. Kindly resend it.

# # Regards"""
# #                     send_mail(sender_email,message)
#             else:
#                 if attachements=='':
#                     print('The document is not in pdf')
#                     message="""Dear Sender, 
#                                             You have not uploaded any pdf here.Kindly upload a pdf.  
                                         
# Regards"""
#                     send_mail(sender_email,message)
#                 elif attachements=='n/a':
#                     print('There is no attachment')
#                     message="""Dear Sender, 
#                                             The mail you sent has no attachments. Kindly resend the mail with a proper attachment. 
                             
# Regards"""
#                     send_mail(sender_email,message)
#           # remove if you want to keep watching

    
