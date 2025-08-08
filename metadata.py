import PyPDF2
from groq import Groq
import mysql.connector
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from mail import send_main_mail
import pprint
import pandas as pd
import re
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from sklearn.cluster import KMeans
# import nltk
# nltk.download('punkt_tab')
# from nltk.tokenize import sent_tokenize

load_dotenv()
def extract(filename, filepath,sender_email):

    # print("in extract")
    # print(filename)
    # print(filepath)
    # start_page=3
    # end_page=11
    
    with open(filepath, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""

        for page in reader.pages:
         text += page.extract_text()
        chunks = chunk_text(text, chunk_size=400, overlap=80)
# print(chunks[0])
    print("hello")
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
    print("hello1")

    # Embed the chunks (list of strings)
    chunk_embeddings = embedder.encode(chunks, show_progress_bar=True)
    print(chunk_embeddings[0])

    

    # Convert to float32 numpy array
    embedding_matrix = np.array(chunk_embeddings).astype('float32')
         
    # Create FAISS index
    
    # index = faiss.IndexFlatIP(embedding_matrix.shape[1])
    
    
    index = faiss.IndexFlatL2(embedding_matrix.shape[1])
    index.add(embedding_matrix)
    
    print(index)
    context1 = get_context("Summarize the key deliverables in this RFP, they should include the key dates(RFP issue date, Pre bid query send date, last date of submission) and the evaluation criteria(QCBS)", k=3,embedder=embedder,index=index,chunks=chunks)
    context2 = get_context("Technical requirement and qualification", k=1,embedder=embedder,index=index,chunks=chunks)
    context3 = get_context("Implementation phase", k=2,embedder=embedder,index=index,chunks=chunks)
    context4=  get_context("service level agreements, objectives",k=3,embedder=embedder,index=index,chunks=chunks)
    
    context = f"""
### Evaluation Criteria Key Dates and Payment milestones
{context1}

### Technical qualification criteria
{context2}

### Implementation phase -> Try making this as detailed as possible and in points
{context3}

### Service level agreement and objectives
{context4}

"""


    prompt = f"""
You are an intelligent and structured language model.

I will give you an input text that may or may not contain details about an RFP (Request for Proposal) document.

Your task is:
- First, determine if the given input is related to an RFP document.
- If it is **not related to an RFP**, respond only with: N/A
- Do not generate anything else in this case

If it **is** an RFP document, generate a concise and structured summary in bullet points under the following headers:
1. Evaluation Criteria
2. Key Dates
3. Technical qualification criteria(in detail)
3. Submission Details
4. Payment milestones
5. Project duration and phases    
6. Financial and legal requirements
7. Language and currency
8. Implementation phases in detailed points
9. Service level objectives(Tell about each objective in points)
10. Other important information

There should be proper bullet points under each header with proper sentences. 


Here is the text: {context}

If the content provided is not related to an RFP, respond with only: **N/A**

There should be no repititon in the response. 
Do not give anything else.


"""
    
    data=metadata(prompt=prompt)
    attachments=[(filename,filepath)]
    if data=="N/A":
        message="""Dear Sender, 
                                The document you uploaded is not a structured one and metadata cannot be extracted from it.Kindly upload a structured dcoument. 
                   Regards"""
        print("cannot send")
        send_main_mail(sender_email,message,attachments)

    else:
     store_in_db(filename,filepath,data)

    

    


def metadata(prompt):
    client = Groq(api_key=os.getenv("api_key"))
    completion = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt}],
        temperature=0,
        max_completion_tokens=1024,
        top_p=1,
        stream=False,
        stop=None,
    )

    metadata = completion.choices[0].message.content
    print(metadata)
    return metadata
    

def count_words(text):
    # Split the text into words using whitespace
    words = text.split()
    return len(words)


def get_context(query,k,embedder,index,chunks):
   query_embedding = embedder.encode([query])[0].astype('float32')
   D, I = index.search(np.array([query_embedding]), k)
   return " ".join([chunks[i] for i in I[0]])

def chunk_text(text, chunk_size=400, overlap=80):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = words[start:end]
        chunks.append(" ".join(chunk))
        start += chunk_size - overlap
    return chunks


def store_in_db(filename,filepath,metadata):
    conn = mysql.connector.connect(
        host=os.getenv("host"), 
        user=os.getenv("user"),  
        password=os.getenv("password"),
        database=os.getenv("database"),
        auth_plugin='mysql_native_password'

    )
    cursor = conn.cursor()
    
    
    sql = "INSERT INTO metadata (filename, filepath, metadata) VALUES (%s, %s, %s)"
    values = (filename, filepath, '')

    try:
        cursor.execute(sql, values)
        conn.commit()
        print(f"Data inserted successfully with ID: {cursor.lastrowid}")
        send_mail(filename,filepath,metadata)
    except Exception as e:
        print("Error inserting data:", e)
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


def send_mail(filename,filepath,metadata):
    from_email = os.getenv("MAIL_ID") 
    from_password = "xmgm eoav tiuy cmyu"  
    smtp_server = "smtp.gmail.com"  
    smtp_port = 587 

   
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] =os.getenv("send_to")
    msg['Subject'] = "New File and Metadata Notification"

    
    # body = f"""
    # Hello,

    # A new file has been processed with the following details:

    # Filename: {filename}

    
    # Filepath: {filepath}



    # Metadata: 
    # {metadata}


    # """
    # msg.attach(MIMEText(body, 'plain'))

    body = f"""
Dear Team,

A new file has been successfully processed. Please find the details below:

------------------------------------------------------------
Filename : {filename}
Filepath : {filepath}
------------------------------------------------------------

Metadata:
{metadata}

------------------------------------------------------------


"""
    msg.attach(MIMEText(body, 'plain'))


   
    
    
    try:

        
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  
        server.login(from_email, from_password)
        
        
        server.sendmail(from_email, msg["To"], msg.as_string())
        # print(f"Email sent to {msg["To"]}")
        print('mail sent')
        
        
        server.quit()
    except Exception as e:
        print(f"Error sending email: {e}")

 











