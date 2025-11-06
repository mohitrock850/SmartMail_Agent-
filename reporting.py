import datetime
from sqlalchemy import desc
from sqlalchemy.orm import Session
from database import Email

def generate_daily_digest(db: Session, top_n=3) -> dict:
    """
    Queries the DB for the top 3 most important emails per category
    from *today* (since midnight).
    """
    try:
        # Get "today" at midnight in UTC
        now_utc = datetime.datetime.now(datetime.UTC)
        start_of_today_utc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Query the database
        all_emails = db.query(Email)\
            .filter(Email.timestamp >= start_of_today_utc)\
            .order_by(desc(Email.priority_score))\
            .all()
        
        if not all_emails:
            return {"message": "No new important emails from today."}

        # --- Categorize the results ---
        categorized_digest = {}
        for email in all_emails:
            category = email.category
            if category not in categorized_digest:
                categorized_digest[category] = []
            
            # This 'if' statement now respects top_n=3
            if len(categorized_digest[category]) < top_n:
                categorized_digest[category].append({
                    "subject": email.subject,
                    "sender": email.sender,
                    "summary": email.summary
                })
        
        return categorized_digest
        
    except Exception as e:
        print(f"Error generating digest: {e}")
        return {"error": f"Could not generate daily digest: {e}"}