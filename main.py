import os
import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from starlette.requests import Request
import pandas as pd

# Import our project modules
from database import init_db, get_db, Email, SessionLocal
from gmail_service import (
    authenticate, 
    fetch_and_process_emails, 
    send_reply,
    get_or_process_email_by_id,
    decrypt_and_process_document 
)
from reporting import generate_daily_digest
templates = Jinja2Templates(directory="templates")
# --- APP SETUP ---
# Global state for credentials and scheduler
google_creds = None
scheduler = BackgroundScheduler(daemon=True)

def scheduled_triage():
    """The job our scheduler will run."""
    print("Scheduler: Running scheduled triage...")
    global google_creds
    if not google_creds:
        print("Scheduler: Cannot run, no Google credentials.")
        return
    if google_creds.expired:
        print("Scheduler: Credentials expired, refreshing...")
        google_creds.refresh()
    
    # Background tasks need to create their own DB session
    db = SessionLocal()
    try:
        # Run the email processing function
        fetch_and_process_emails(db, google_creds, max_results=25)
    except Exception as e:
        print(f"Scheduler: Error during triage: {e}")
    finally:
        db.close()
        print("Scheduler: Triage finished.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    print("--- 🚀 SmartMail Agent API Starting Up ---")
    load_dotenv()
    init_db()  # Create database tables if they don't exist
    
    global google_creds
    google_creds = authenticate()
    if not google_creds:
        print("\n" + "="*50)
        print("WARNING: Google credentials not found or expired.")
        print("Run 'python cli.py' in your terminal to log in.")
        print("The API will run, but email fetching will fail.")
        print("="*50 + "\n")
    
    # Setup and start scheduler
    scheduler.add_job(scheduled_triage, 'cron', hour=9, minute=0)
    scheduler.start()
    print("--- Startup complete. Server is running. ---")
    
    yield
    
    # --- SHUTDOWN ---
    print("--- Shutting down scheduler ---")
    scheduler.shutdown()

# Create the FastAPI app instance
app = FastAPI(lifespan=lifespan)

# --- Define Request Models ---
class ReplyRequest(BaseModel):
    reply_body: str

class DocumentPasswordRequest(BaseModel):
    messageId: str
    password: str

# --- NEW: Define a request model for our add-on ---
class ProcessRequest(BaseModel):
    messageId: str
    threadId: str

# --- API ENDPOINTS ---

@app.get("/")
def index():
    """Simple test endpoint to see if the server is running."""
    return {"message": "SmartMail Agent API is running!"}

@app.post("/process-email")
def process_one_email(request: ProcessRequest, db: Session = Depends(get_db)):
    """
    Main endpoint for the Gmail Add-on.
    Checks for readable attachments and encryption.
    """
    # ... (rest of function is unchanged, it will now return
    # {"status": "needs_password", "filename": "report.pdf"}
    # if it finds an encrypted PDF/Word)
    print(f"API: Add-on requested processing for {request.messageId}")
    global google_creds
    if not google_creds:
        raise HTTPException(status_code=503, detail="Not authenticated with Google.")
    
    email_data = get_or_process_email_by_id(db, google_creds, request.messageId)
    
    if not email_data:
        raise HTTPException(status_code=500, detail="Failed to get or process email")
    
    if isinstance(email_data, dict):
        if email_data.get("status") == "needs_password":
            print(f"Returning needs_password status for {request.messageId}")
            return email_data
    
    return {
        "id": email_data.email_id,
        "sender": email_data.sender,
        "subject": email_data.subject,
        "summary": email_data.summary,
        "category": email_data.category,
        "priority": email_data.priority_score,
        "draft_reply": email_data.draft_reply
    }

@app.post("/process-document")
def decrypt_document(request: DocumentPasswordRequest, db: Session = Depends(get_db)):
    """
    Decrypts a PDF/DOCX using a password and processes it.
    """
    print(f"API: Document decryption requested for {request.messageId}")
    global google_creds
    if not google_creds:
        raise HTTPException(status_code=503, detail="Not authenticated with Google.")
        
    result = decrypt_and_process_document(
        db, google_creds, request.messageId, request.password
    )
    
    if isinstance(result, dict) and "error" in result:
        print(f"Decryption error: {result['error']}")
        raise HTTPException(status_code=400, detail=result["error"])
    
    # Success! Return the newly processed data
    return {
        "id": result.email_id,
        "sender": result.sender,
        "subject": result.subject,
        "summary": result.summary,
        "category": result.category,
        "priority": result.priority_score,
        "draft_reply": result.draft_reply
    }

@app.post("/triage")
def trigger_triage(db: Session = Depends(get_db)):
    """
    Manually triggers email fetching and processing for multiple unread emails.
    """
    print("API: Manual triage triggered...")
    global google_creds
    if not google_creds:
        raise HTTPException(status_code=503, detail="Not authenticated with Google. Run 'python cli.py'.")
    
    result = fetch_and_process_emails(db, google_creds, max_results=10)
    return {"message": result}

@app.get("/daily_report")
def get_daily_report(db: Session = Depends(get_db)):
    """
    Generates and returns the daily digest as categorized JSON.
    """
    print("API: Generating daily report...")
    digest = generate_daily_digest(db)
    
    if "error" in digest:
        raise HTTPException(status_code=500, detail=digest["error"])
        
    return digest

@app.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    """
    Returns the top 10 most important emails from *today*.
    """
    print("API: Generating summary for *today*...")
    try:
        # --- NEW: Add date filter ---
        now_utc = datetime.datetime.now(datetime.UTC)
        start_of_today_utc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        
        top_emails = db.query(Email)\
            .filter(Email.timestamp >= start_of_today_utc)\
            .order_by(Email.priority_score.desc())\
            .limit(10)\
            .all()
        
        results = [
            {
                "id": email.email_id,
                "sender": email.sender,
                "subject": email.subject,
                "summary": email.summary,
                "category": email.category,
                "priority": email.priority_score
            } for email in top_emails
        ]
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reply/{email_id}")
def send_email_reply(email_id: str, request: ReplyRequest):
    """
    Sends a reply to the email with the given ID.
    """
    print(f"API: Sending reply to {email_id}...")
    global google_creds
    if not google_creds:
        raise HTTPException(status_code=503, detail="Not authenticated with Google. Run 'python cli.py'.")
    
    result = send_reply(
        creds=google_creds,
        original_email_id=email_id,
        reply_text=request.reply_body
    )
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result['error'])
    
    return {"message": "Reply sent successfully!", "details": result}
@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard(request: Request, db: Session = Depends(get_db)):
    """
    Queries the database and renders the analytics dashboard.
    """
    print("API: Generating dashboard...")
    try:
        # 1. Query all emails from the database
        all_emails = db.query(Email).all()
        
        if not all_emails:
            # Handle empty database
            return templates.TemplateResponse("dashboard.html", {
                "request": request, 
                "chart_data": {}
            })

        # 2. Use Pandas to easily count categories
        data = [{"category": email.category} for email in all_emails]
        df = pd.DataFrame(data)
        
        # Get counts like {"Work": 10, "Personal": 5, ...}
        category_counts = df['category'].value_counts().to_dict()
        
        # 3. Render the HTML page, injecting the data
        return templates.TemplateResponse("dashboard.html", {
            "request": request, 
            "chart_data": category_counts
        })

    except Exception as e:
        print(f"Error generating dashboard: {e}")
        return HTMLResponse(content=f"<h1>Error generating dashboard: {e}</h1>", status_code=500)