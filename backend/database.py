import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy import event
from datetime import datetime

# 1. The SQLite connection string (creates a file in the same folder)
DATABASE_URL = "sqlite:///./leads_engine.db"

# 2. Engine setup (check_same_thread=False is required for FastAPI background tasks)
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# 3. 🌟 THE MAGIC COMMAND 🌟 Enable WAL mode for SQLite concurrency
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ==========================================
# SQLALCHEMY ORM MODELS
# ==========================================
class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    domain = Column(String, unique=True, index=True)
    industry = Column(String)
    location = Column(String)
    lead_score = Column(Integer)
    priority = Column(String)
    reason = Column(Text)
    signals = Column(JSON)  # Standard JSON works perfectly in SQLite via SQLAlchemy
    confidence = Column(Float)
    source = Column(String)
    
    contacts = relationship("Contact", back_populates="company")

class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    name = Column(String(255))
    designation = Column(String(255))
    
    linkedin_url = Column(String(500), unique=True, index=True) 
    relevance_score = Column(Integer, nullable=True)
    rank = Column(Integer, nullable=True)

    contact_status = Column(String(50), default="New") 
    last_contact_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    follow_up_date = Column(DateTime, nullable=True)
    
    company = relationship("Company", back_populates="contacts")

class SearchHistory(Base):
    __tablename__ = "search_history"
    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String)
    input_parameters = Column(JSON)
    leads_generated = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)