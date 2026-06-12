"""
===============================================================================
File: schemas.py
Project: Lead Contact Generator
Description: 
    This module defines the Pydantic models used for data validation, 
    serialization, and type hinting across the FastAPI application. It acts 
    as the strict gatekeeper for data entering and leaving the API.
    
    Key Responsibilities:
    - Defines Request models (e.g., scraping parameters, CRM updates) to 
      ensure incoming JSON payloads are perfectly structured and typed.
    - Defines Response models to securely format and filter database records 
      before transmitting them to the React frontend.
    - Automatically powers the interactive Swagger UI / OpenAPI documentation.
    - Bridges the gap between SQLAlchemy ORM objects and JSON-serializable 
      dictionaries (via `orm_mode` or `from_attributes=True`).
===============================================================================
"""
from pydantic import BaseModel, Field
from typing import List, Optional

# ---------------------------------------------------------
# Contact Schema (For the top 3 decision makers)
# ---------------------------------------------------------
class ContactSchema(BaseModel):
    name: str = Field(..., description="The full name of the contact.")
    designation: str = Field(..., description="The job title or role of the contact.")
    
    # FIX: Changed from HttpUrl to Optional[str] to prevent crashing on empty strings ("")
    linkedin_url: Optional[str] = Field("", description="The absolute URL to the contact's LinkedIn profile. Can be empty if not found.")
    
    relevance_score: Optional[int] = Field(None, ge=1, le=100, description="Score from 1 to 100 based on how relevant this person is for sales outreach.")
    rank: Optional[int] = Field(None, ge=1, le=3, description="Rank this contact 1, 2, or 3. 1 being the best person to contact.")

# ---------------------------------------------------------
# Company Analysis Schema (What the AI returns after scraping)
# ---------------------------------------------------------
class CompanyAnalysisSchema(BaseModel):
    name: str = Field(..., description="The official name of the company.")
    domain: str = Field(..., description="The primary website domain of the company.")
    industry: str = Field(..., description="The specific industry the company operates in.")
    location: Optional[str] = Field(None, description="Headquarters location, if available.")
    size: Optional[str] = Field(None, description="Estimated number of employees.")
    lead_score: int = Field(..., ge=0, le=100, description="A calculated score from 0 to 100 representing how well this company matches the target criteria.")
    reason: str = Field(..., description="A short, one-sentence explanation for the lead score.")
    signals: dict = Field(..., description="A JSON object containing key buying signals found on the website (e.g., 'hiring': true).")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="AI's confidence in this analysis from 0.0 to 1.0.")
    top_contacts: List[ContactSchema] = Field(..., max_length=3, description="A strict list of exactly the top 3 decision-makers found.")