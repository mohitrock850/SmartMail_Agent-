import os.path
import base64
import email.message
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
import pypdf

from ai_processor import (
    summarize_email, 
    classify_email, 
    draft_reply, 
    get_priority_score
)
from database import Email
from doc_processor import extract_document_text, check_if_encrypted

# --- CONFIGURATION ---
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'
USER_CATEGORIES = ["Urgent", "Work", "Personal", "Finance", "Newsletter"]

# --- NEW: Hardcoded salt for key derivation. ---
# In a real-world app, you might store this in .env
SALT = b'salt_password123' 

def authenticate():
    """--- Phase 1: Step 3 --- Handles user authentication."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Credentials expired. Refreshing...")
            creds.refresh(Request())
        else:
            print("No valid credentials found. Starting authentication...")
            print("You must run 'python cli.py' from the terminal to authorize.")
            return None
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            
    print("Authentication successful.")
    return creds

def get_email_body(payload):
    """Parses the email payload (plaintext or HTML)."""
    try:
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        return base64.urlsafe_b64decode(data).decode('utf-8')
                elif 'parts' in part:
                    body = get_email_body(part)
                    if body:
                        return body
        elif 'body' in payload and payload['mimeType'] == 'text/plain':
            data = payload['body'].get('data')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8')

        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/html':
                    data = part['body'].get('data')
                    if data:
                        html_content = base64.urlsafe_b64decode(data).decode('utf-8')
                        soup = BeautifulSoup(html_content, 'html.parser')
                        return soup.get_text(separator=' ', strip=True)
                elif 'parts' in part:
                    body = get_email_body(part) 
                    if body:
                        return body
        elif 'body' in payload and payload['mimeType'] == 'text/html':
            data = payload['body'].get('data')
            if data:
                html_content = base64.urlsafe_b64decode(data).decode('utf-8')
                soup = BeautifulSoup(html_content, 'html.parser')
                return soup.get_text(separator=' ', strip=True)
    except Exception as e:
        print(f"Error while parsing body: {e}")
    return None

# --- HERE IS THE FUNCTION DEFINITION ---
def _parse_sender_email(raw_sender: str) -> str:
    """Extracts just the email address from a raw 'From' header."""
    if '<' in raw_sender and '>' in raw_sender:
        try:
            return raw_sender.split('<')[-1].split('>')[0]
        except Exception:
            return raw_sender  # Fallback
    return raw_sender

def _find_document_attachment(parts):
    """
    Recursively searches email parts for a .pdf or .docx file.
    Returns (attachment_id, filename) or (None, None).
    """
    for part in parts:
        filename = part.get('filename')
        if filename and (filename.lower().endswith('.pdf') or filename.lower().endswith('.docx')):
            if 'body' in part and 'attachmentId' in part['body']:
                return part['body']['attachmentId'], filename
        
        if 'parts' in part:
            att_id, fname = _find_document_attachment(part['parts'])
            if att_id:
                return att_id, fname
    return None, None


def _get_attachment_data(service, message_id, attachment_id):
    """Fetches and decodes attachment data."""
    attachment = service.users().messages().attachments().get(
        userId='me', messageId=message_id, id=attachment_id
    ).execute()
    data_b64 = attachment['data']
    return base64.urlsafe_b64decode(data_b64)


def get_or_process_email_by_id(db: Session, creds, message_id: str):
    """
    Handles a single email.
    1. Checks DB.
    2. If not in DB, fetches from Gmail.
    3. Checks for PDF/DOCX attachments.
    4. If attachment found:
       a. Checks if encrypted. If yes, returns "needs_password".
       b. If not encrypted, reads text, processes, saves, and returns data.
    5. If no attachment, processes email body as normal.
    """
    
    # 1. Check DB first
    db_email = db.query(Email).filter(Email.email_id == message_id).first()
    if db_email:
        if db_email.encrypted:
            print(f"Email {message_id} is encrypted and awaiting password.")
            
            # --- THIS IS THE FIX ---
            # We must also return the messageId here, which was missing.
            return {"status": "needs_password", 
                    "filename": db_email.subject, 
                    "id": message_id} # <-- THIS 'id' KEY WAS MISSING
            
        else:
            print(f"Email {message_id} found in DB. Returning cached data.")
            return db_email # It's a normal, processed email

    # 2. Not in DB. Fetch from Gmail.
    print(f"Email {message_id} not in DB. Fetching...")
    service = build('gmail', 'v1', credentials=creds)
    
    try:
        email = service.users().messages().get(
            userId='me', id=message_id, format='full'
        ).execute()
        
        payload = email.get('payload', {})
        headers = payload.get('headers', [])
        parts = payload.get('parts', [])
        
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        raw_sender = next((h['value'] for h in headers if h['name'] == 'From'), 'No Sender')
        sender = _parse_sender_email(raw_sender)

        # 3. Check for PDF/DOCX attachments
        attachment_id, filename = _find_document_attachment(parts)
        
        # 4. Attachment FOUND
        if attachment_id:
            print(f"Found attachment: {filename}")
            
            # 4a. Download it and check for encryption
            file_data = _get_attachment_data(service, message_id, attachment_id)
            
            if check_if_encrypted(file_data, filename):
                print(f"File {filename} is password-protected.")
                # Save a placeholder
                placeholder = Email(
                    email_id=message_id, sender=sender, subject=filename,
                    summary="[Encrypted File]", category="Encrypted",
                    priority_score=3, draft_reply="[File is encrypted]",
                    encrypted=True
                )
                db.add(placeholder)
                db.commit()
                # This return IS correct and was already working
                return {"status": "needs_password", "filename": filename, "id": message_id}
            
            # 4b. File is NOT encrypted. Read, process, and save.
            print(f"File {filename} is not encrypted. Reading text...")
            content_to_process = extract_document_text(file_data, filename)
            email_subject = subject
            
        # 5. No attachment found
        else:
            print("No supported attachments. Processing email body.")
            content_to_process = get_email_body(payload)
            if not content_to_process:
                content_to_process = email.get('snippet', '[Could not parse body]')
            email_subject = subject
            filename = None
        
        # --- Run AI Processing (on either body or file text) ---
        summary = summarize_email(content_to_process)
        category = classify_email(content_to_process, USER_CATEGORIES)
        draft = draft_reply(content_to_process)
        priority = get_priority_score(category)
        
        new_email_entry = Email(
            email_id=message_id,
            sender=sender,
            subject=email_subject,
            summary=summary,
            category=category,
            priority_score=priority,
            draft_reply=draft,
            encrypted=False
        )
        db.add(new_email_entry)
        db.commit() 
        db.refresh(new_email_entry)
        
        return new_email_entry

    except Exception as e:
        print(f'An unexpected error occurred: {e}')
        # Clean up placeholder if processing failed
        db_email = db.query(Email).filter(Email.email_id == message_id).first()
        if db_email:
            db.delete(db_email)
            db.commit()
        return None
        
def decrypt_and_process_document(db: Session, creds, message_id: str, password: str):
    """
    Fetches a protected doc, decrypts it,
    processes it with AI, and updates the database.
    """
    service = build('gmail', 'v1', credentials=creds)
    
    try:
        db_email = db.query(Email).filter(Email.email_id == message_id).first()
        if not db_email or not db_email.encrypted:
            return {"error": "Email not found or not marked as encrypted."}
            
        filename = db_email.subject
        
        email = service.users().messages().get(
            userId='me', id=message_id, format='full'
        ).execute()
        parts = email.get('payload', {}).get('parts', [])
        attachment_id, _ = _find_document_attachment(parts)
        
        if not attachment_id:
            return {"error": "Could not find attachment in email."}

        file_data = _get_attachment_data(service, message_id, attachment_id)
        
        # This function now handles all decryption and extraction
        content_to_process = extract_document_text(file_data, filename, password)

    # --- SIMPLIFIED: We only need to catch PermissionError ---
    except PermissionError as e:
        print(f"Decryption failed: {e}")
        return {"error": "Invalid Password"}
    except Exception as e:
        print(f"Processing failed: {e}")
        return {"error": str(e)}
        
    # 5. Process the decrypted text with AI
    print("Decryption successful! Processing content...")
    summary = summarize_email(content_to_process)
    # ... (rest of the function is unchanged)
    
    category = classify_email(content_to_process, USER_CATEGORIES)
    draft = draft_reply(content_to_process)
    priority = get_priority_score(category)
    
    db_email.summary = summary
    db_email.category = category
    db_email.priority_score = priority
    db_email.draft_reply = draft
    db_email.encrypted = False 
    
    headers = email.get('payload', {}).get('headers', [])
    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), filename)
    db_email.subject = subject
    
    db.commit()
    db.refresh(db_email)
    return db_email

def fetch_and_process_emails(db: Session, creds, max_results=5):
    """--- Phase 2, 3 & 5: Fetch, Process, AND Store ---"""
    if not creds:
        return "Authentication required."
        
    processed_count = 0
    service = build('gmail', 'v1', credentials=creds)
    
    try:
        # We add 'category:primary' to the query string
        print(f"\nFetching last {max_results} unread 'Primary' emails...")
        result = service.users().messages().list(
            userId='me', 
            labelIds=['INBOX'], 
            q='is:unread category:primary',  # <-- This is our filter
            maxResults=max_results
        ).execute()
        
        messages = result.get('messages', [])
        if not messages:
            return "No unread 'Primary' messages."

        for msg in messages:
            msg_id = msg['id']
            
            existing_email = db.query(Email).filter(Email.email_id == msg_id).first()
            if existing_email:
                print(f"Email {msg_id} already processed. Skipping.")
                continue 
            
            email = service.users().messages().get(
                userId='me', id=msg_id, format='full'
            ).execute()
            
            payload = email['payload']
            headers = payload['headers']
            
            subject = next(h['value'] for h in headers if h['name'] == 'Subject')
            raw_sender = next(h['value'] for h in headers if h['name'] == 'From')
            
            # --- HERE IS THE CORRECTED FUNCTION CALL ---
            sender = _parse_sender_email(raw_sender)
            
            body = get_email_body(payload)
            if not body:
                body = email.get('snippet', '[Could not parse body]')

            summary = summarize_email(body)
            category = classify_email(body, USER_CATEGORIES)
            draft = draft_reply(body) # This now includes your signature
            priority = get_priority_score(category)
            
            new_email_entry = Email(
                email_id=msg_id,
                sender=sender,  # This is the clean email
                subject=subject,
                summary=summary,
                category=category,
                priority_score=priority,
                draft_reply=draft,
                encrypted=False
            )
            db.add(new_email_entry)
            db.commit() 
            processed_count += 1
            print(f"Processed and saved email {msg_id}.")

        return f"Triage complete. Processed {processed_count} new emails."

    except HttpError as error:
        print(f'An error occurred: {error}')
        return f"An error occurred: {error}"
    except Exception as e:
        print(f'An unexpected error occurred: {e}')
        return f"An unexpected error occurred: {e}"

def send_reply(creds, original_email_id: str, reply_text: str) -> dict:
    """
    Sends a reply to a specific email.
    """
    service = build('gmail', 'v1', credentials=creds)
    
    try:
        # 1. Get the original email to reply to
        original_msg = service.users().messages().get(
            userId='me', id=original_email_id, format='metadata'
        ).execute()
        
        headers = original_msg['payload']['headers']
        
        # 2. Find the correct headers to make a proper reply "thread"
        subject = next(h['value'] for h in headers if h['name'].lower() == 'subject')
        original_from = next(h['value'] for h in headers if h['name'].lower() == 'from')
        original_msg_id = next(h['value'] for h in headers if h['name'].lower() == 'message-id')

        # 3. Create the reply message
        msg = email.message.EmailMessage()
        msg.set_content(reply_text)
        msg['To'] = _parse_sender_email(original_from) # Reply to the original sender
        msg['Subject'] = f"Re: {subject}" if not subject.lower().startswith('re:') else subject
        
        # 4. Set headers to make it a "thread"
        msg['In-Reply-To'] = original_msg_id
        msg['References'] = original_msg_id

        # 5. Encode and send
        encoded_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        create_message_body = {'raw': encoded_message}
        
        sent_msg = service.users().messages().send(
            userId='me',
            body=create_message_body
        ).execute()
        
        return sent_msg

    except HttpError as error:
        print(f'An error occurred: {error}')
        return {"error": str(error)}
    except Exception as e:
        print(f'An unexpected error occurred: {e}')
        return {"error": str(e)}