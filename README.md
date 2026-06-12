# Valency AI Lead Generation CRM

Valency AI is an automated, full-stack B2B lead generation pipeline. It leverages LLMs for intelligent business qualification, headless browser automation for data scraping, and a robust FastAPI/SQLite architecture to manage lead tracking.

## 🚀 Production Architecture
* **Frontend:** React (Vite), compiled to static assets served by **Nginx** (Port ).
* **Backend:** Python FastAPI, managed as a **Windows Background Service** (Port ).
* **Database:** SQLite (local persistence).
* **Reverse Proxy:** Nginx routes external requests to the frontend or proxies API calls to the backend.

---

## 🏗️ Deployment Strategy (Windows Server)

### 1. Prerequisites
Ensure the target Windows Server has the following installed:
* **Python 3.10+** (Added to System PATH)
* **Node.js 18+** (LTS)
* **Nginx** (Extract to `C:\nginx`)
* **NSSM** (For service management)
* **Git for Windows**

### 2. Frontend Deployment (Nginx)
1. Navigate to `/frontend` and generate the static build:
   ```bash
   echo VITE_API_BASE_URL="http://YOUR_SERVER_IP/api" > .env
   npm install
   npm run build
