"""
===============================================================================
File: main.py
Project: Lead Contact Generator
Description: 
    This is the primary entry point and central orchestrator for the FastAPI 
    backend. It defines the REST API endpoints, handles CORS configuration for 
    the frontend, and manages the asynchronous background tasks. 
    
    Key Responsibilities:
    - Initiates the SQLite database connection and table creation.
    - Exposes the `/api/generate` endpoint to trigger the AI scraping pipeline.
    - Exposes the `/api/history` endpoint to serve the CRM dashboard.
    - Orchestrates the sequential flow of data: Scraper -> AI Engine -> 
      LinkedIn Enrichment -> SQLite Database.
      
    Note: Includes specific event-loop policy adjustments to ensure Playwright 
    operates correctly on Windows Server environments.
===============================================================================
"""

import sys
import asyncio
import uuid
import io
import csv
import os
import datetime
from sqlalchemy.orm import joinedload
from urllib.parse import urlparse

# CRITICAL FIX FOR WINDOWS PLAYWRIGHT + FASTAPI
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from datetime import datetime


from database import SessionLocal, engine, Base, Company, Contact, SearchHistory

Base.metadata.create_all(bind=engine)

# Import our individual engine services
from services.scraper import search_companies_via_serpapi, extract_website_text
from services.ai_engine import analyze_company_with_ai
from services.enrichment import find_linkedin_contacts

app = FastAPI(title="Lead Generation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DualLogger(object):
    def __init__(self, filename="debug.log"):
        self.terminal = sys.stdout
        # Open in append mode so it keeps a running history
        self.log = open(filename, "a", encoding="utf-8")
        
        # Add a startup timestamp to separate sessions in the log file
        startup_marker = f"\n\n{'='*50}\n🚀 SERVER STARTED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{'='*50}\n"
        self.terminal.write(startup_marker)
        self.log.write(startup_marker)
        self.log.flush()

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush() # Force write to disk immediately

    def flush(self):
        self.terminal.flush()
        self.log.flush()

# Intercept all print statements and errors, mirroring them to debug.log
sys.stdout = DualLogger("debug.log")
sys.stderr = sys.stdout
# ==========================================
# EPHEMERAL JOB TRACKER
# ==========================================
JOBS_DB = {}

# ==========================================
# REQUEST BLUEPRINTS (Pydantic)
# ==========================================
class LeadGenerationRequest(BaseModel):
    industry: str
    location: str
    sales_inputs: dict

class ContactUpdate(BaseModel):
    contact_status: str | None = None
    notes: str | None = None
    follow_up_date: str | None = None

# ==========================================
# THE BACKGROUND ENGINE (PostgreSQL)
# ==========================================
async def background_lead_generator(job_id: str, request: LeadGenerationRequest):
    db = SessionLocal()
    
    try:
        # ==========================================
        # 1. THE STRICT COMPULSORY ROLE CHECK
        # ==========================================
        raw_target_roles = (
            request.sales_inputs.get("Target Roles") or 
            request.sales_inputs.get("target_roles") or 
            request.sales_inputs.get("targetRoles") or 
            request.sales_inputs.get("TargetRoles")
        )
        
        # If the role is missing or completely empty, abort the job immediately
        if not raw_target_roles or str(raw_target_roles).strip() == "":
            JOBS_DB[job_id]["status"] = "failed"
            JOBS_DB[job_id]["error"] = "CRITICAL: 'Target Roles' is a compulsory field. Please enter a role to search for."
            print(f"❌ Job {job_id} aborted: Target Roles missing from frontend.")
            return

        # Format the roles cleanly into a list
        if isinstance(raw_target_roles, str):
            target_roles = [role.strip() for role in raw_target_roles.split(",")]
        else:
            target_roles = raw_target_roles

        print(f"🎯 AI IS INSTRUCTED TO LOOK ONLY FOR: {target_roles}")

        # 👇 Treat the frontend volume input as the "Company Quota"
        requested_companies = int(request.sales_inputs.get("Number of Leads Required", 3))
        JOBS_DB[job_id]["status"] = "scraping_google"
        
        # Fetch 15 results so we have backups if the AI rejects some
        companies = search_companies_via_serpapi(request.industry, request.location, num_results=50)
        
        if not companies:
            JOBS_DB[job_id]["status"] = "failed"
            JOBS_DB[job_id]["error"] = "No companies found on Google."
            return

        JOBS_DB[job_id]["status"] = "analyzing_ai"
        analyzed_leads = []
        
        for company in companies:
            # 👇 THE QUOTA CHECK: Stop when we have enough validated COMPANIES 👇
            if len(analyzed_leads) >= requested_companies:
                print(f"\n🎯 Target of {requested_companies} valid companies reached! Stopping engine.")
                break
                
            # STRICT HOMEPAGE EXTRACTOR: Strip away deep links and sub-pages
            raw_url = company["url"]
            try:
                # Add schema if missing so urlparse works correctly
                if not raw_url.startswith('http'):
                    raw_url = 'https://' + raw_url
                parsed = urlparse(raw_url)
                clean_root_domain = parsed.netloc.replace('www.', '')
            except:
                clean_root_domain = raw_url

            print(f"\nProcessing: {company['name']} ({clean_root_domain})...")
            text = await extract_website_text(company["url"])

            # If scraping failed (bot protection, JS timeout, etc.), use an empty string.
            # passes_basic_heuristic() returns True for empty text so the company still
            # gets sent to the AI, which will likely score it 0 without content — but
            # at least the company isn't silently discarded due to a scrape failure.
            text = text or ""
                
            analysis = await analyze_company_with_ai(
                company_name=company["name"],
                company_url=f"https://{clean_root_domain}", # Feed AI the clean homepage
                website_text=text,
                sales_inputs=request.sales_inputs,
                target_location=request.location
            )
            
            if analysis and analysis.get("lead_score", 0) >= 50:
                # 1. Get the clean name from the AI
                clean_company_name = analysis.get("name")
                
                # 2. If the AI somehow failed to return a name, fall back to the domain
                if not clean_company_name or clean_company_name == "":
                    clean_company_name = clean_root_domain.split('.')[0].capitalize()

                # 3. Proceed with enrichment
                # NOTE: The old domain-name mismatch guardrail was removed.
                # It rejected legitimate companies whose names don't literally
                # appear in their domain (e.g. "Equations Work" → eqw.ai,
                # "Augmented Transformations" → augtrans.com).
                # Third-party sites are already blocked structurally by
                # EXCLUDED_DOMAINS, the .gov TLD guard, and the post-AI
                # aggregator check in scraper.py — this check was redundant.
                JOBS_DB[job_id]["status"] = f"enriching_{clean_company_name}"
                print(f"📦 RAW FRONTEND DATA: {request.sales_inputs}")

                # 4. LinkedIn enrichment
                raw_contacts = await find_linkedin_contacts(clean_company_name, target_roles, request.location)

                # All contacts from find_linkedin_contacts already have is_match=True
                # (the enrichment layer filters them). Cap at 3 per company.
                real_contacts = [c for c in raw_contacts if c.get("is_match") is True][:3]

                # 5. Save company to DB (single path — deduped by domain)
                # ---------------------------------------------------------
                # Step 5: Save or Update the Company in SQLite
                # ---------------------------------------------------------
                existing_company = db.query(Company).filter(Company.domain == clean_root_domain).first()
                
                if not existing_company:
                    # 🟢 BRAND NEW COMPANY
                    new_company = Company(
                        name=clean_company_name,
                        domain=clean_root_domain,
                        industry=request.industry,
                        location=request.location,
                        lead_score=analysis.get("lead_score"),
                        reason=analysis.get("reason"),
                        source="AI_Pipeline",
                    )
                    db.add(new_company)
                    db.flush() # Get the new ID
                    company_db_id = new_company.id
                    
                    # 🚨 ADD THIS FLAG FOR REACT: Tells the frontend this is a new lead
                    analysis["is_db_duplicate"] = False 
                    
                else:
                    # 🟡 ALREADY IN DATABASE
                    company_db_id = existing_company.id
                    
                    # Optional: Update the lead score if the new one is higher
                    if analysis.get("lead_score", 0) > (existing_company.lead_score or 0):
                        # Force the types so Pylance stops complaining:
                        existing_company.lead_score = int(analysis.get("lead_score", 0))# type: ignore
                        existing_company.reason = str(analysis.get("reason", ""))# type: ignore
                        
                    # 🚨 ADD THIS FLAG FOR REACT: Triggers the Yellow "Repeat" Badge!
                    analysis["is_db_duplicate"] = True
                    
                db.commit()
                    
                # 6. SAVE CONTACTS & CLEAN FOR FRONTEND
                # 6. SAVE CONTACTS & CLEAN FOR FRONTEND
                duplicate_count = 0  
                
                if real_contacts:
                    seen_urls = set() 
                    clean_frontend_contacts = [] 
                    
                    for c in real_contacts:
                        url = c.get("linkedin_url", "")
                        
                        if url and url in seen_urls:
                            continue # Skip the twin!
                        if url:
                            seen_urls.add(url)
                            
                        clean_frontend_contacts.append(c) 
                        
                        existing_contact = db.query(Contact).filter(Contact.linkedin_url == url).first()
                        if not existing_contact:
                            new_contact = Contact(
                                company_id=company_db_id,
                                name=c.get("name", "Unknown"),
                                designation=c.get("designation", "Unknown"),
                                linkedin_url=url,
                                notes=c.get("pitch_angle", "")
                            )
                            db.add(new_contact)
                        else:
                            duplicate_count += 1  
                            
                else:
                    clean_frontend_contacts = []
                    print(f"   ⚠️ No valid contacts found for {clean_company_name}, but saving company anyway.")

                # 🚨 ADD THIS HERE: Guarantee everything saves immediately, even if contacts are empty!
                db.commit()

                # 👇 3. Send the CLEAN list to React
                analysis["domain"] = clean_root_domain
                analysis["top_contacts"] = clean_frontend_contacts 
                analysis["duplicates_hidden"] = duplicate_count

                # 7. Add to our quota list so the loop knows we successfully found a company
                analyzed_leads.append(analysis)
                
        try:
            new_history = SearchHistory(
                user_name="Sales User",  # You can change this if you add logins later
                input_parameters=request.model_dump(),  # Saves Industry, Location, and all Sales Inputs as JSON
                leads_generated=len(analyzed_leads)
            )
            db.add(new_history)
            db.commit()
            print(f"✅ Search History logged successfully!")
        except Exception as hist_err:
            print(f"⚠️ Failed to log search history: {hist_err}")
            db.rollback()
        # 👆 END OF NEW BLOCK 👆

        JOBS_DB[job_id]["status"] = "completed"
        JOBS_DB[job_id]["results"] = analyzed_leads
        print(f"🎉 Job {job_id} Complete! Pipeline successfully extracted data for {len(analyzed_leads)} companies.")            
    
    except Exception as e:
        db.rollback() 
        JOBS_DB[job_id]["status"] = "failed"
        JOBS_DB[job_id]["error"] = str(e)
        print(f"❌ Background task failed: {e}")
    finally:
        db.close()

# ==========================================
# THE API ENDPOINTS
# ==========================================

@app.get("/")
async def root():
    return {"message": "Lead Generation API is awake and running!"}

@app.post("/api/generate-leads")
async def start_lead_generation(request: LeadGenerationRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    JOBS_DB[job_id] = {
        "status": "queued",
        "results": [],
        "error": None
    }
    background_tasks.add_task(background_lead_generator, job_id, request)
    return {"message": "Job started", "job_id": job_id}

@app.get("/api/jobs/{job_id}")
async def check_job_status(job_id: str):
    if job_id not in JOBS_DB:
        return {"error": "Job not found."}
    return JOBS_DB[job_id]

@app.get("/api/jobs")
async def get_all_jobs():
    return JOBS_DB

@app.put("/api/contacts/{contact_id}")
async def update_contact(contact_id: int, payload: ContactUpdate):
    """Updates CRM status, notes, and dates for a specific contact."""
    db = SessionLocal()
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if contact:
        if payload.contact_status:
            contact.contact_status = payload.contact_status  # type: ignore[assignment]
        if payload.notes is not None:
            contact.notes = payload.notes                    # type: ignore[assignment]

        # Safely parse the date from React and save it to the DB
        if payload.follow_up_date is not None:
            if payload.follow_up_date == "":
                contact.follow_up_date = None                # type: ignore[assignment]
            else:
                try:
                    contact.follow_up_date = datetime.strptime(  # type: ignore[assignment]
                        payload.follow_up_date, "%Y-%m-%d"
                    )
                except ValueError:
                    pass
                    
        db.commit()
    db.close()
    return {"message": "Updated"}

@app.get("/api/export")
async def export_leads_csv():
    """Generates a CSV of all saved leads and contacts."""
    db = SessionLocal()
    contacts = db.query(Contact, Company).join(Company).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Company", "Domain", "Contact Name", "Designation", "LinkedIn", "Status", "Notes"])
    
    for contact, company in contacts:
        writer.writerow([company.name, company.domain, contact.name, contact.designation, contact.linkedin_url, contact.contact_status, contact.notes])
        
    db.close()
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads_export.csv"}
    )
    
@app.get("/api/history")
async def get_crm_history():
    """Fetches all saved companies and contacts for the CRM History tab."""
    db = SessionLocal()
    try:
        companies = db.query(Company).options(joinedload(Company.contacts)).all()
        
        history_results = []
        for comp in companies:
                
            history_results.append({
                "id": comp.id,
                "name": comp.name,
                "domain": comp.domain,
                "industry": comp.industry,
                "location": comp.location, 
                "lead_score": comp.lead_score,
                "reason": comp.reason,
                "top_contacts": [
                    {
                        "id": c.id, 
                        "name": c.name,
                        "designation": c.designation,
                        "linkedin_url": c.linkedin_url,
                        "contact_status": c.contact_status,
                        "notes": c.notes,
                        "follow_up_date": c.follow_up_date.strftime("%Y-%m-%d") if c.follow_up_date else ""
                    } for c in comp.contacts
                ]
            })
            
        history_results.sort(key=lambda x: x["lead_score"], reverse=True)
        return history_results
    finally:
        db.close()