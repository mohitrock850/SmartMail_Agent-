import os 
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.orm.session import Session
import datetime

# --- Database Setup ---
# Using SQLite, which stores the DB in a single file
DATABASE_URL = os.getenv("DATABASE_URL")

Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Database Model ---
class Email(Base):
    """
    This is the database model for storing our email metadata.
    It matches the fields from Phase 5, Step 8.
    """
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(String, unique=True, index=True) # The Gmail message ID
    sender = Column(String)
    subject = Column(String)
    summary = Column(Text)
    category = Column(String)
    priority_score = Column(Integer)
    draft_reply = Column(Text)
    encrypted = Column(Boolean, default=False) # For Phase 4
    timestamp = Column(DateTime, default=datetime.datetime.now(datetime.UTC))

# --- Helper Functions ---
def init_db():
    """Creates all the database tables."""
    print("Initializing database...")
    Base.metadata.create_all(bind=engine)

def get_db():
    """
    FastAPI dependency to get a DB session.
    This is a generator that yields a session.
    It ensures the database session is always closed
    after the request is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

