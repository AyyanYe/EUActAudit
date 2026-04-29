# PROJECT_CONTEXT.md

## AI-Auditor (EUActAudit) – Complete Project Overview

### 1. Executive Summary

**Project Name:** EUActAudit (formerly AI-Auditor)

**Core Value Proposition:** An automated Governance, Risk, and Compliance (GRC) platform specifically designed for EU AI Act (2025) compliance. Instead of calculating arbitrary compliance scores, it highlights key compliance issues in company workflows and provides actionable advice on how to fix them.

**Key Innovation:** Transforms generic technical audits into a "Governance State Machine" that interviews users to build a Legal Compliance Profile, distinguishing between "High Risk" (Annex III) and "Limited Risk" (Article 50) AI systems.

---

### 2. Business Logic & Governance Model

**Operating Model:** Deterministic State Machine with Human-in-the-Loop interviews (not a chatbot).

**Hard-Coded Compliance Rules:**

- **Prohibited Practices (Art. 5):** Immediate stop for Social Scoring, Emotion Recognition in Schools/Workplace, Real-time Biometric ID in public.
- **High Risk (Annex III):** Recruitment (HR), Critical Infrastructure, Education, Essential Services (Credit/Insurance), Law Enforcement.
- **Role Logic (Art. 3 & 25):** Provider (model builder → heavy obligations) vs. Deployer (model buyer → lighter obligations).
- **Limited Risk (Art. 50):** Chatbots and Deepfakes must disclose AI nature.

---

### 3. System Architecture

#### Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | React (Vite), TypeScript, Tailwind CSS, Shadcn/UI |
| Backend | Python (FastAPI), Uvicorn |
| AI/LLM | LangChain, OpenAI GPT-4o (via OpenRouter) |
| Auth | Clerk |
| Databases | SQLite (MVP) / PostgreSQL (production); Pinecone/Chroma (planned Vector DB) |

#### Dual-Database Architecture

1. **Relational DB (SQLite/PostgreSQL):** Source of truth. Stores Projects → Facts → Obligations → InterviewLogs. Enables audit trails.

2. **Vector DB (Pinecone/Chroma - Future):** RAG layer. Stores EU AI Act text for contextual retrieval when rules trigger.

---

### 4. Logic Layer (The "Brain")

| File | Purpose |
|------|---------|
| `backend/core/engine.py` | Fact Extraction: Uses GPT-4o to listen to chat logs and extract JSON facts. |
| `backend/core/risk_rules.py` | Risk Judge: Deterministic Python script applying IF/THEN legal logic (no hallucinations). |
| `backend/routers/interview.py` | API Handler: Connects frontend to engine, manages /chat loop and PDF generation. |
| `backend/database.py` | Data Schema: Project, Fact, Obligation models. |

---

### 5. Current Codebase State

**Backend (`/workspaces/AI-Auditor/backend`):**
- `main.py` – Entry point with /interview router
- `database.py` – Relational schema (NEW)
- `routers/interview.py` – Chat loop and PDF logic (NEW)
- `core/engine.py` – Fact extraction with LangChain (NEW)
- `core/risk_rules.py` – EU AI Act compliance logic (NEW)

**Frontend (`/workspaces/AI-Auditor/frontend`):**
- `App.tsx` – Routing with new /governance route
- `pages/GovernanceChat.tsx` – Split-screen MVP (Chat + Live Dashboard) (NEW)
- `services/api.ts` – Backend integration with GovernanceService (UPDATED)

---

### 6. Development Roadmap

#### Phase 1: Smart Interview ✅ (Current/Completed)
- ✅ Relational DB Schema
- ✅ Fact Extraction with GPT-4o
- ✅ Risk Rules Implementation
- ✅ Split-Screen Dashboard

#### Phase 2: Deliverable 🔄 (Next)
- ⬜ PDF Report Generation (`/report` endpoint)
- ⬜ Frontend Download Button

#### Phase 3: RAG Integration 📅 (Future)
- ⬜ Ingest EU AI Act into Vector Store
- ⬜ Connect engine to Vector Store for "Why?" contextual answers

---

### 7. Critical Files for Modifications

When requesting changes, reference these core files:

- **Backend Logic:** `backend/core/risk_rules.py` (legal rules), `backend/core/engine.py` (AI logic)
- **Database:** `backend/database.py` (state schema)
- **Frontend UI:** `frontend/src/pages/GovernanceChat.tsx` (user experience)
- **API Integration:** `frontend/src/services/api.ts` (backend communication)
