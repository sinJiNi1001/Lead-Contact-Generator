import os
import urllib.parse
import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

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

# ==========================================
# SQLALCHEMY ORM MODELS (Mapped to your exact SQL)
# ==========================================

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True, nullable=False)
    industry = Column(String(100))
    location = Column(String(255))
    size = Column(String(50))
    lead_score = Column(Integer)
    priority = Column(String(50))
    reason = Column(Text)
    signals = Column(JSONB)
    confidence = Column(Float)
    source = Column(String(100))
    date_created = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    contacts = relationship("Contact", back_populates="company", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="company", cascade="all, delete-orphan")

class Contact(Base):
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"))
    name = Column(String(255), nullable=False)
    designation = Column(String(255))
    linkedin_url = Column(String(500), unique=True, nullable=False)
    relevance_score = Column(Integer)
    rank = Column(Integer)
    primary_flag = Column(Boolean, default=False)
    contact_status = Column(String(50), default='New')
    last_contact_date = Column(DateTime)

    # Relationships
    company = relationship("Company", back_populates="contacts")
    activities = relationship("Activity", back_populates="contact")

class Activity(Base):
    __tablename__ = "activities"
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"))
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100))
    notes = Column(Text)
    date = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="activities")
    contact = relationship("Contact", back_populates="activities")

class SearchHistory(Base):
    __tablename__ = "search_history"
    
    id = Column(Integer, primary_key=True)
    user_name = Column(String(100))
    input_parameters = Column(JSONB)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    leads_generated = Column(Integer)