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
                # 1. Get the clean name from the AI
                clean_company_name = analysis.get("name")
                
                # 2. If the AI somehow failed to return a name, fall back to the domain
                if not clean_company_name or clean_company_name == "":
                    clean_company_name = clean_root_domain.split('.')[0].capitalize()

                # 🛡️ 3. THE THIRD-PARTY MISMATCH GUARDRAIL 🛡️
                # Check if the domain name has at least some overlap with the company name
                domain_core = clean_root_domain.split('.')[0].lower()
                name_core = clean_company_name.lower().replace(" ", "").replace("-", "")
                
                # If the first 4 letters of the domain aren't in the company name (and vice versa)
                if domain_core[:4] not in name_core and name_core[:4] not in domain_core:
                    print(f"   🛡️ Guardrail triggered: '{clean_company_name}' does not match domain '{clean_root_domain}'. Rejecting third-party site.")
                    continue # Skip this company and move to the next Google result
                
                # 4. Proceed with enrichment
                JOBS_DB[job_id]["status"] = f"enriching_{clean_company_name}"
                print(f"📦 RAW FRONTEND DATA: {request.sales_inputs}")
                
                # Directly call the LinkedIn scraper
                raw_contacts = await find_linkedin_contacts(clean_company_name, target_roles, request.location)
                
                # THE SEMANTIC AI BOUNCER 
                real_contacts = []
                for contact in raw_contacts:
                    if contact.get("is_match") is True:
                        real_contacts.append(contact)
                    else:
                        print(f"🚫 AI Bouncer Dropped {contact.get('name', 'Unknown')} - Title '{contact.get('designation')}' not a semantic match.")
                
                # 👇 THE SPAM FILTER: Cap the contacts at 3 per company 👇
                # This ensures we don't flood the CRM with 10 executives from one place.
                real_contacts = real_contacts[:3]
                
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
                                
                            # 5. 🚀 SAVE THE COMPANY (Even if no contacts are found!) 🚀
                existing_company = db.query(Company).filter(Company.domain == clean_root_domain).first()
                if not existing_company:
                    new_comp = Company(
                        name=clean_company_name,
                        domain=clean_root_domain,
                        industry=request.industry,
                        location=request.location,
                        lead_score=analysis.get("lead_score", 0),
                        reason=analysis.get("reason", "")
                    )
                    db.add(new_comp)
                    db.commit()
                    db.refresh(new_comp)
                    company_db_id = new_comp.id
                else:
                    company_db_id = existing_company.id

                # 6. SAVE CONTACTS (Only if the AI actually found valid ones)
                if real_contacts:
                    for c in real_contacts:
                        existing_contact = db.query(Contact).filter(Contact.linkedin_url == c.get("linkedin_url")).first()
                        if not existing_contact:
                            new_contact = Contact(
                                company_id=company_db_id,
                                name=c.get("name", "Unknown"),
                                designation=c.get("designation", "Unknown"),
                                linkedin_url=c.get("linkedin_url", ""),
                                
                            )
                            db.add(new_contact)
                    db.commit()
                else:
                    print(f"   ⚠️ No valid contacts found for {clean_company_name}, but saving company anyway.")
                    
                analysis["domain"] = clean_root_domain
                analysis["top_contacts"] = real_contacts if real_contacts else []    

                # 7. Add to our quota list so the loop knows we successfully found a company
                analyzed_leads.append(analysis)
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