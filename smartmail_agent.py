import os.path
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv  
from bs4 import BeautifulSoup

from ai_processor import (
    summarize_email, 
    classify_email, 
    draft_reply, 
    get_priority_score
)

from database import init_db, get_db, Email

from reporting import generate_daily_digest


# --- CONFIGURATION ---
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

# --- NEW: User-defined categories from Phase 3 ---
USER_CATEGORIES = ["Urgent", "Work", "Personal", "Finance", "Newsletter"]


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
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES, redirect_uri='http://localhost:5001/oauth2callback') 
            creds = flow.run_local_server(port=5001)
        
        with open(TOKEN_FILE, 'w') as token:
            print(f"Saving credentials to {TOKEN_FILE}...")
            token.write(creds.to_json())
            
    print("Authentication successful.")
    return creds

def get_email_body(payload):
    """
    Parses the email payload to find the body.
    It prioritizes 'text/plain', but will fall back to 'text/html'
    and strip the HTML tags.
    """
    try:
        # 1. Look for 'text/plain' first
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        return base64.urlsafe_b64decode(data).decode('utf-8')
                # Recursive call for nested parts (e.g., multipart/alternative)
                elif 'parts' in part:
                    body = get_email_body(part)
                    if body:
                        return body
        elif 'body' in payload and payload['mimeType'] == 'text/plain':
            data = payload['body'].get('data')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8')

        # 2. If no 'text/plain', look for 'text/html'
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/html':
                    data = part['body'].get('data')
                    if data:
                        html_content = base64.urlsafe_b64decode(data).decode('utf-8')
                        # Use BeautifulSoup to strip HTML tags
                        soup = BeautifulSoup(html_content, 'html.parser')
                        return soup.get_text(separator=' ', strip=True)
                elif 'parts' in part:
                    body = get_email_body(part) # Recursive call
                    if body:
                        return body # This might return HTML text from a nested part
        elif 'body' in payload and payload['mimeType'] == 'text/html':
            data = payload['body'].get('data')
            if data:
                html_content = base64.urlsafe_b64decode(data).decode('utf-8')
                soup = BeautifulSoup(html_content, 'html.parser')
                return soup.get_text(separator=' ', strip=True)

    except Exception as e:
        print(f"Error while parsing body: {e}")
    # 3. Fallback if no body is found
    return None

def fetch_and_process_emails(creds, max_results=5):
    """
    --- Phase 2, 3 & 5: Fetch, Process, AND Store ---
    Fetches, sends to AI, and saves metadata to the database.
    """
    # --- NEW: Get a database session ---
    db = get_db()
    
    try:
        service = build('gmail', 'v1', credentials=creds)
        
        print(f"\nFetching last {max_results} unread emails...")
        result = service.users().messages().list(
            userId='me', 
            labelIds=['INBOX'], 
            q='is:unread', 
            maxResults=max_results
        ).execute()
        
        messages = result.get('messages', [])
        
        if not messages:
            print("No unread messages found.")
            return

        print("--- Processing and Storing Emails ---")
        
        for msg in messages:
            msg_id = msg['id']
            
            # --- NEW: Check for Duplicates ---
            existing_email = db.query(Email).filter(Email.email_id == msg_id).first()
            if existing_email:
                print(f"Email {msg_id} already processed. Skipping.")
                continue # Move to the next email
            
            # --- Process as before ---
            email = service.users().messages().get(
                userId='me', id=msg_id, format='full'
            ).execute()
            
            payload = email['payload']
            headers = payload['headers']
            
            subject = next(h['value'] for h in headers if h['name'] == 'Subject')
            sender = next(h['value'] for h in headers if h['name'] == 'From')
            body = get_email_body(payload)
            
            if not body:
                body = email.get('snippet', '[Could not parse body]')

            # --- AI PROCESSING ---
            summary = summarize_email(body)
            category = classify_email(body, USER_CATEGORIES)
            draft = draft_reply(body)
            
            # --- NEW: Get Priority Score ---
            priority = get_priority_score(category)
            
            # --- NEW: Create Database Object ---
            new_email_entry = Email(
                email_id=msg_id,
                sender=sender,
                subject=subject,
                summary=summary,
                category=category,
                priority_score=priority,
                draft_reply=draft,
                encrypted=False # Default for now
            )
            
            # --- NEW: Add to Database ---
            db.add(new_email_entry)
            db.commit() # Save the change
            
            # --- Display Results ---
            print("\n" + "="*50)
            print(f"From:    {sender}")
            print(f"Subject: {subject}")
            print("---")
            print(f"✅ AI Summary:  {summary}")
            print(f"✅ AI Category: {category}")
            print(f"✅ AI Priority: {priority}")
            print(f"✅ AI Draft:    {draft}")
            print(f"💾 Email {msg_id} saved to database.")
            print("="*50)

    except HttpError as error:
        print(f'An error occurred: {error}')
    except Exception as e:
        print(f'An unexpected error occurred: {e}')
    finally:
        # --- NEW: Always close the session ---
        db.close()
        print("\nDatabase session closed.")
def main():
    print("--- 🚀 Welcome to the SmartMail Agent ---")
    
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found in .env file.")
        return

    # --- NEW: Initialize the database ---
    init_db()

    # Phase 1: Authenticate
    creds = authenticate()
    
    if creds:
        # Phase 2, 3 & 5: Fetch, Process, and Store
        fetch_and_process_emails(creds)
        # Now that we've processed new emails, generate the digest
        print("\n--- 📊 Generating Daily Digest ---")
        digest = generate_daily_digest()
        print(digest)
        print("---------------------------------")

if __name__ == '__main__':
    main()