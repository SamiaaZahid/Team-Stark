# ⚡ NovaWorks Technologies - AI Project Manager (Meeting to Execution)
> **The Infinity Hack '26 Challenge MVP (Node.js + Express + Prisma & React + Vite)**  
> *Transform unstructured meeting transcripts into fully validated, assigned projects and tasks with strict Role-Based Access Control (RBAC).*

---

## 📌 1. Project Overview & Features

NovaWorks Technologies is a software agency in Lahore, Pakistan specializing in websites, mobile apps, and AI solutions. This Project Management CRM eliminates manual project setup by taking multi-stakeholder meeting transcripts and automatically extracting structured projects, task breakdowns, assignees, deadlines, and effort hour estimates.

### ✨ Key Features
- **10 Seeded Demo Accounts**: Pre-configured Admin, 3 Managers (PM01, PM02, PM03), and 6 Developers (DEV01 - DEV06) with password `Demo123!`.
- **JWT Authentication & Login**: Standard login with email & password. Displays demo accounts reference guide on the login screen for easy testing. No "Switch Demo User" feature (users sign in/out normally).
- **Strict Role-Based Access Control (RBAC)**: Enforced directly at the **Express API layer**:
  - **Admin**: Complete system overview, all projects and tasks, exclusive access to `POST /api/ai/transcript`.
  - **Managers (Ayesha, Bilal, Hina)**: Scoped strictly to projects they manage (`managerId == currentUser.id`). Unauthorized requests return `403 Forbidden`.
  - **Developers / Agents (Ali, Hamza, Sara, Usman, Zain, Maryam)**: Scoped strictly to projects containing tasks assigned to them; and when viewing project details, they can **only** see their own assigned tasks (other developers' tasks are completely hidden). Includes dedicated **"My Assigned Tasks"** dashboard (`GET /api/tasks/my`).
- **AI Transcript Automation Endpoint (`POST /api/ai/transcript`)**:
  - Uses the official `@google/genai` SDK with model from `process.env.GEMINI_MODEL` (default: `gemini-3.8-flash`).
  - `temperature: 0`, `responseMimeType: "application/json"`.
  - Full system instruction containing team directory, business rules, revisions, and exclusion rules.
  - Quota, error, and offline handling with built-in high-precision deterministic verification engine.
- **Transactional Integrity**: Prisma transaction (`prisma.$transaction`) guarantees all-or-nothing save.

---

## 🛠️ 2. Technology Stack

- **Backend**:
  - Node.js & Express.js
  - Prisma ORM with SQLite (or PostgreSQL)
  - JWT (`jsonwebtoken`) & `bcryptjs`
  - Official Google Gen AI SDK (`@google/genai`)
- **Frontend**:
  - React 18 & Vite
  - Modern, responsive custom UI
- **Database**:
  - SQLite via Prisma (`backend/prisma/dev.db`)

---

## 📋 3. Seeded Demo Accounts Table

Every account is pre-seeded with password: `Demo123!`

| ID | Name | Role | Email | Specialization | Skills | Password |
|---|---|---|---|---|---|---|
| **ADMIN** | Admin | `ADMIN` | `admin@novaworks.example` | Administrator | Company overview, transcript creation | `Demo123!` |
| **PM01** | Ayesha Khan | `MANAGER` | `ayesha@novaworks.example` | Manager / Web PM | Web projects, client coordination | `Demo123!` |
| **PM02** | Bilal Ahmed | `MANAGER` | `bilal@novaworks.example` | Manager / Mobile PM | Mobile projects, delivery planning | `Demo123!` |
| **PM03** | Hina Malik | `MANAGER` | `hina@novaworks.example` | Manager / AI PM | AI projects, requirement review | `Demo123!` |
| **DEV01** | Ali Raza | `AGENT` | `ali@novaworks.example` | Agent / Full-Stack | React, frontend integration | `Demo123!` |
| **DEV02** | Hamza Shah | `AGENT` | `hamza@novaworks.example` | Agent / Full-Stack | Node.js, databases, APIs | `Demo123!` |
| **DEV03** | Sara Noor | `AGENT` | `sara@novaworks.example` | Agent / App Developer | Flutter, mobile UI | `Demo123!` |
| **DEV04** | Usman Tariq | `AGENT` | `usman@novaworks.example` | Agent / App Developer | Flutter, integration, testing | `Demo123!` |
| **DEV05** | Zain Abbas | `AGENT` | `zain@novaworks.example` | Agent / AI Developer | LLMs, extraction, prompts | `Demo123!` |
| **DEV06** | Maryam Asif | `AGENT` | `maryam@novaworks.example` | Agent / AI Developer | Retrieval, document processing | `Demo123!` |

---

## 🚀 4. Quickstart & Local Setup

### Option A: One-Click Run (Windows)
Double-click `run.bat` at the root of the project. It will initialize the database, seed accounts, and launch both backend (port 5000) and frontend (port 5173).

### Option B: Manual Commands

#### 1. Setup & Start Backend
```bash
cd backend
npm install
npx prisma db push
node prisma/seed.js
node src/server.js
```
*Backend runs on `http://localhost:5000`.*

#### 2. Start Frontend
```bash
cd frontend
npm install
npm run dev
```
*Frontend runs on `http://localhost:5173`.*

---

## 🧪 5. Automated Backend Verification Test

Run the automated test suite to verify JWT authentication, RBAC, and transcript extraction accuracy against the organizer answer key:
```bash
cd backend
node test_api.js
```

---

## 📊 6. Organizer Verification Reference Cross-Check

| Project | Client | Manager | Deadline | Tasks Count | Total Hours |
|---|---|---|---|---|---|
| **UrbanCart Website** | UrbanCart Clothing | Ayesha (`PM01`) | `2026-10-20` | 4 | 40 hrs |
| **QuickServe Mobile App** | QuickServe Services | Bilal (`PM02`) | `2026-10-24` | 4 | 46 hrs |
| **HelpDeskPro AI Assistant** | HelpDeskPro Solutions | Hina (`PM03`) | `2026-10-22` | 4 | 38 hrs |
| **Total** | | | | **12 Tasks** | **124 Hours** |

### Critical Checks Implemented:
- UrbanCart deadline is **20 October**, not 18 October.
- UrbanCart integration task deadline is **19 October**, not 17 October.
- QuickServe integration estimate is **10 hours**, not 8 hours.
- HelpDeskPro testing belongs to **Maryam**, not Zain.
- **Kamran** is ignored (not an employee).
- Excluded rejected scope items (payments, inventory, live maps, driver tracking, real email/ticketing).
