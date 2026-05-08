import os
import urllib.parse
import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from datetime import datetime




# Load variables from the .env file
load_dotenv()

# 1. Grab the raw password from your .env file
raw_password = os.getenv("DB_PASSWORD")

if not raw_password:
    raise ValueError("DB_PASSWORD is missing from your .env file!")

# 2. Automatically encode special characters (like the '@' symbol)
encoded_password = urllib.parse.quote_plus(raw_password)

# 3. Construct the final connection string safely
DATABASE_URL = f"postgresql://postgres:{encoded_password}@localhost:5432/lead_intel_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ==========================================
# SQLALCHEMY ORM MODELS (Mapped to your exact SQL)
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
    signals = Column(JSON)
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