import sys
import asyncio
import uuid
import io
import csv
from sqlalchemy.orm import joinedload

from urllib.parse import urlparse

# CRITICAL FIX FOR WINDOWS PLAYWRIGHT + FASTAPI
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Import our database setup and relational models
from database import SessionLocal, Company, Contact, SearchHistory

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

# ==========================================
# THE BACKGROUND ENGINE (with PostgreSQL)
# ==========================================
async def background_lead_generator(job_id: str, request: LeadGenerationRequest):
    db = SessionLocal()
    
    try:
        requested_leads = int(request.sales_inputs.get("Number of Leads Required", 3))
        JOBS_DB[job_id]["status"] = "scraping_google"
        
        # Fetch 15 results so we have backups if the AI rejects some
        companies = search_companies_via_serpapi(request.industry, request.location, num_results=15)
        
        if not companies:
            JOBS_DB[job_id]["status"] = "failed"
            JOBS_DB[job_id]["error"] = "No companies found on Google."
            return

        JOBS_DB[job_id]["status"] = "analyzing_ai"
        analyzed_leads = []
        
        for company in companies:
            if len(analyzed_leads) >= requested_leads:
                print(f"\n🎯 Target of {requested_leads} valid leads reached! Stopping engine.")
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
            
            if not text:
                continue
                
            analysis = await analyze_company_with_ai(
                company_name=company["name"],
                company_url=f"https://{clean_root_domain}", # Feed AI the clean homepage
                website_text=text,
                sales_inputs=request.sales_inputs,
                target_location=request.location
            )
            
            if analysis and analysis.get("lead_score", 0) >= 50:
                clean_company_name = analysis.get("name", company["name"])
                JOBS_DB[job_id]["status"] = f"enriching_{clean_company_name}"
                
                target_roles = request.sales_inputs.get("Target Roles", ["CTO", "CEO"])
                real_contacts = find_linkedin_contacts(clean_company_name, target_roles)
                
                final_new_contacts = []
                
                # Check DB for existing company using the STRICT ROOT DOMAIN
                existing_company = db.query(Company).filter(Company.domain == clean_root_domain).first()
                
                if not existing_company:
                    new_company = Company(
                        name=clean_company_name,
                        domain=clean_root_domain,      # Forces the clean homepage link!
                        industry=request.industry,     # Forces what you typed in the form!
                        location=request.location,     # Forces what you typed in the form!
                        lead_score=analysis.get("lead_score"),
                        priority=analysis.get("priority", "Medium"),
                        reason=analysis.get("reason"),
                        signals=analysis.get("signals"),
                        confidence=analysis.get("confidence_score"),
                        source="AI_Pipeline"
                    )
                    db.add(new_company)
                    db.flush() 
                    company_db_id = new_company.id
                else:
                    company_db_id = existing_company.id

                # Deduplicate & Save Contacts
                if real_contacts:
                    seen_urls = set() 
                    for contact in real_contacts:
                        linkedin_url = contact.get("linkedin_url")
                        
                        if linkedin_url and "unknown" not in linkedin_url.lower():
                            if linkedin_url in seen_urls:
                                continue 
                                
                            existing_contact = db.query(Contact).filter(Contact.linkedin_url == linkedin_url).first()
                            
                            if not existing_contact:
                                new_contact = Contact(
                                    company_id=company_db_id,
                                    name=contact.get("name"),
                                    designation=contact.get("designation"),
                                    linkedin_url=linkedin_url,
                                    relevance_score=contact.get("relevance_score"),
                                    rank=contact.get("rank"),
                                    contact_status="New"
                                )
                                db.add(new_contact)
                                seen_urls.add(linkedin_url)
                                final_new_contacts.append(contact) 
                
                db.commit() 
                analysis["domain"] = clean_root_domain 
                analysis["top_contacts"] = final_new_contacts 
                
                if len(final_new_contacts) > 0:
                    analyzed_leads.append(analysis)
        
        JOBS_DB[job_id]["status"] = "completed"
        JOBS_DB[job_id]["results"] = analyzed_leads
        print(f"✅ Job {job_id} Complete! Saved {len(analyzed_leads)} leads.")            
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
    """Updates CRM status and notes for a specific contact."""
    db = SessionLocal()
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if contact:
        if payload.contact_status: contact.contact_status = payload.contact_status
        if payload.notes is not None: contact.notes = payload.notes
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
            if not comp.contacts:
                continue 
                
            history_results.append({
                "id": comp.id,
                "name": comp.name,
                "domain": comp.domain,
                "industry": comp.industry,
                
                # FIX: Added the location field so the frontend doesn't say "Unknown"
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
                        "notes": c.notes
                    } for c in comp.contacts
                ]
            })
            
        history_results.sort(key=lambda x: x["lead_score"], reverse=True)
        return history_results
    finally:
        db.close()