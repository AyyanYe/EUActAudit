# EUActAudit — Complete Project Explanation

This document describes the **EUActAudit** application in full: purpose, features, user workflow, architecture, data model, and implementation details. It is intended for presentations, onboarding, and technical reference.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Mission and Value Proposition](#2-mission-and-value-proposition)
3. [Key Features](#3-key-features)
4. [User Workflow and Conversation Flow](#4-user-workflow-and-conversation-flow)
5. [Risk Classification (EU AI Act)](#5-risk-classification-eu-ai-act)
6. [Architecture](#6-architecture)
7. [Data Model and Database](#7-data-model-and-database)
8. [Core Backend Logic](#8-core-backend-logic)
9. [Frontend Structure](#9-frontend-structure)
10. [Security, Guardrails, and Anti-Manipulation](#10-security-guardrails-and-anti-manipulation)
11. [Report Generation](#11-report-generation)
12. [Deployment and Environment](#12-deployment-and-environment)

---

## 1. Project Overview

**EUActAudit** is an AI-driven **EU AI Act Compliance Consultant**. It helps companies building or deploying AI systems in the European market to:

- **Classify** their system into the regulation’s risk buckets (Prohibited, High-Risk, Limited Risk, Minimal Risk).
- **Run a conversational audit** that gathers business context, operational workflow, and evidence for compliance.
- **Map gaps** to specific articles (e.g. Article 14 human oversight, Article 10 data governance) and show live obligation status in a sidebar.
- **Guide remediation** (e.g. “planned” or “under review”) and **generate a PDF compliance report** for human review.

The tool acts as a bridge between the legal text of the EU AI Act (Regulation (EU) 2024/1689) and practical product development, so non-lawyers can understand what applies to their system and what evidence is needed.

**Target users:** Product owners, compliance officers, and developers who need a practical view of EU AI Act obligations without reading the full regulation.

---

## 2. Mission and Value Proposition

- **Intelligent gatekeeper:** Classify every project into the Act’s legal buckets and block or flag prohibited use cases.
- **Automatic risk detection:** Use natural language (project description + chat) to infer domain, purpose, and context and assign risk level.
- **Collaborative audit:** Conduct a structured interview (not a one-off form) to collect facts, workflow, and compliance evidence; support “turning red to green” with clear next steps.
- **Real-time transparency:** Live workflow map and compliance sidebar so users see obligations and status as they talk.
- **Kill switch:** For prohibited practices (e.g. certain emotion recognition, social scoring), terminate the session with a firm, professional message and do not offer compliance measures.
- **Anti-manipulation:** Do not accept vague or blanket “we’re compliant” answers; require concrete evidence and use confidence scoring to trigger verification when needed.

---

## 3. Key Features

| Feature | Description |
|--------|-------------|
| **Risk gatekeeper** | Deterministic rules (plus optional LLM pre-classification in Technical Audit) map facts to Prohibited / High-Risk / Limited / Minimal. |
| **Conversational audit** | Chat-based interview: gathers domain, role, purpose, data types, automation, context, human oversight; then asks for step-by-step workflow. |
| **Live compliance sidebar** | Obligations (e.g. Art. 14, Art. 10, Art. 15, Art. 12, Art. 50) with status: Pending, Under Review, Planned Remediation, Gap Detected, Met. Updates as the conversation progresses. |
| **Live workflow map** | Visual list of the user’s described process steps; compliance questions can be tied to specific steps. |
| **Kill switch** | Prohibited use cases (Article 5) get a clear “banned” message and session can be terminated (TERMINATED state). |
| **Confidence-aware dialogue** | Each fact has a 0–100 confidence (hybrid: deterministic + LLM). Below-threshold facts trigger verification before being used for compliance. |
| **Anti-manipulation** | No rubber-stamping: requires specific evidence; blanket affirmations can be downgraded; directive logic refuses to declare compliance on request. |
| **Report generation** | Once the assessment is sufficiently complete, user can download a PDF report with risk justification, obligation breakdown, and recommendations. |
| **Dashboard** | Aggregated metrics: total/active/completed assessments, compliance rate, risk distribution, obligation breakdown, recent projects, activity timeline, top compliance gaps. |
| **Technical Audit** | Separate flow: bias/fairness audit of an AI model (run tests, view history). Uses `AuditRun` and optional LLM risk pre-classification (`risk_logic.py`). |

---

## 4. User Workflow and Conversation Flow

### 4.1 High-Level Steps

1. **Start** — User creates a project (name + short description). Backend creates a `Project` and returns the first bot message; interview starts in state `INIT`.
2. **Intake** — Bot collects core facts: **domain** (e.g. recruitment, education), **role** (provider vs deployer), **purpose** (e.g. ranking candidates, emotion recognition).
3. **Discovery** — Bot collects: **data_type** (e.g. biometric, personal), **automation** (fully_automated, human_in_the_loop), **context** (e.g. workplace, education), **human_oversight** (present, absent, partial, planned).
4. **Workflow** — Bot asks for a **step-by-step** description of the process (data in → AI steps → decisions → output). At least two workflow steps are required to leave this state.
5. **Checkpoint / Assessment** — Risk rules run; obligations are created/updated. Bot asks about unresolved topics (human oversight, data governance, accuracy/robustness, record-keeping, transparency), verifies low-confidence facts, and handles “stuck” or parked topics. For HIGH risk, mandatory topics are driven by `HIGH_RISK_MANDATORY_TOPICS`.
6. **Completion** — When mandatory topics are addressed and assessment is complete, bot summarizes and suggests generating the Compliance Report. For **prohibited** systems, bot delivers the “banned” message and does not offer compliance measures (TERMINATED).

### 4.2 State Machine

The interview is driven by a **deterministic state machine** in `backend/core/state_machine.py`:

| State | Meaning | Exit condition |
|-------|--------|----------------|
| **INIT** | Project created, no facts yet | After first message → INTAKE |
| **INTAKE** | Gathering domain, role, purpose | When all three are non-empty → DISCOVERY |
| **DISCOVERY** | Gathering data_type, automation, context, human_oversight | When all four are non-empty → WORKFLOW |
| **WORKFLOW** | Gathering operational workflow steps | When `workflow_steps` has ≥2 steps → CHECKPOINT |
| **CHECKPOINT** | Running risk rules, evaluating completeness | When all critical facts present → ASSESSMENT |
| **ASSESSMENT** | Final state; obligations identified; report available | Terminal |
| **TERMINATED** | Session closed (e.g. prohibited use case) | Terminal |

- **Confidence level** (LOW / MEDIUM / HIGH) is computed from how many of the critical facts are present (plus a bonus for workflow steps); it is used in messaging and UX, not for state transitions.
- **Deductions** (risk rules, obligation creation): run in INTAKE and DISCOVERY only for **prohibited-practice detection**; full obligation creation runs in CHECKPOINT and ASSESSMENT. WORKFLOW does not run deductions.

### 4.3 Directive Priorities (Governance Engine)

The bot does not speak from a fixed script. A **directive** (short instruction) is chosen by priority; the LLM then generates the actual reply. Priorities (simplified) are:

- **PRIORITY -1:** Workflow gathering (when in WORKFLOW state and fewer than 2 steps).
- **PRIORITY -0.5:** User asked about a specific topic (e.g. “Explain Article 14”) — answer that first.
- **PRIORITY -0.25:** Verify low-confidence facts (CHECKPOINT/ASSESSMENT only; one verification per turn).
- **PRIORITY 0:** Article 14 blocking (HIGH risk, human oversight absent/no, remediation not yet offered).
- **Sequential gap handler:** For HIGH risk, cycle through mandatory topics (human_oversight, data_governance, accuracy_robustness, record_keeping), with topic parking, stuck detection, and round-robin so the bot does not loop on one topic.
- **Report blocker explanation:** If user asks for the report but topics are still unresolved, explain which topics block the report and what evidence is needed.
- **State-aware directives:** Prohibited (UNACCEPTABLE) message; exemption probe (PENDING_PROHIBITED); LIMITED transparency; HIGH missing mandatory topics; report-ready summary; missing-facts fallback.

---

## 5. Risk Classification (EU AI Act)

Risk is determined by **deterministic rules** in `backend/core/risk_rules.py` (and optionally pre-classified by LLM in Technical Audit via `risk_logic.py`). The governance chat uses **only** the rule engine.

### 5.1 Levels

- **UNACCEPTABLE (Prohibited)** — Article 5:
  - Emotion recognition in workplace/education (with exemption probe: medical/safety? If “no” → banned).
  - Social scoring.
  - Real-time remote biometric identification in public spaces (with exemption probe).
  - When confirmed prohibited, the system returns a BLOCKED message and can set compliance_status to TERMINATED.

- **HIGH** — Annex III high-risk domains:
  - Domains: recruitment/HR, education, critical infrastructure, credit/insurance, biometrics, law enforcement, migration, justice, etc.
  - Role splits obligations: **Provider** (QMS Art. 16, Conformity Art. 43, Data Governance Art. 10, Human Oversight by Design Art. 14) vs **Deployer** (Human Oversight Art. 26, Monitoring/Logging, Data Governance Art. 10, Mandatory Human Oversight Art. 14).
  - Common for both: Accuracy & Robustness (Art. 15), Record Keeping (Art. 12).
  - If human oversight is absent/no/partial or automation is fully_automated, an Art. 14 oversight obligation is added (wording differs for provider vs deployer).

- **LIMITED** — Transparency (Article 50):
  - Chatbots / interaction capability → “Users must be informed they are talking to an AI.”
  - Content generation (image/video/audio) → “Output must be machine-readable as AI generated.”

- **MINIMAL** — Default when no higher risk applies.

### 5.2 Exemption Probe

For practices that *might* be prohibited (e.g. emotion recognition in education/workplace), the engine can return `PENDING_PROHIBITED` and a directive asks **one** clarifying question (e.g. medical/safety exemption). If the user answers “no” → UNACCEPTABLE and BLOCKED message. If “yes” → fall through to HIGH-risk evaluation.

---

## 6. Architecture

### 6.1 High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React + Vite)                         │
│  Dashboard │ Compliance Chat │ Technical Audit │ History & Reports │ Legal   │
│  Clerk (auth) │ Tailwind │ Shadcn-style UI │ Recharts │ React Router         │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        │ HTTPS (REST)
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND (FastAPI)                               │
│  /interview (start, chat, projects, project/:id, generate-report)           │
│  /audit (run-bias-test, history)                                             │
│  /dashboard (stats)                                                          │
│  CORS, Clerk JWT validation (optional get_user_id_optional / get_clerk_user) │
└─────────────────────────────────────────────────────────────────────────────┘
         │                    │                           │
         │                    │                           │
         ▼                    ▼                           ▼
┌─────────────────┐  ┌─────────────────────┐  ┌─────────────────────────────┐
│  PostgreSQL     │  │  OpenRouter (GPT-4o)│  │  RAG (TF-IDF in-memory +    │
│  (e.g. Neon)    │  │  Fact extraction +  │  │  eu_ai_act_articles.json)   │
│  Projects,      │  │  directive-based    │  │  Article context for        │
│  Facts,         │  │  response generation│  │  prompts                    │
│  Obligations,   │  │                     │  │                              │
│  Logs,          │  └─────────────────────┘  └─────────────────────────────┘
│  Workflows,     │
│  AuditRuns      │
└─────────────────┘
```

### 6.2 Component Responsibilities

| Layer | Responsibility |
|-------|----------------|
| **Frontend** | Auth (Clerk), routing, Dashboard (stats from `/dashboard/stats`), Compliance Chat (start, send message, list/get project, generate report), Technical Audit (bias test, history), History & Reports, Privacy/Terms. |
| **Backend API** | REST endpoints; auth via `Authorization: Bearer <Clerk JWT>`; project scoping by `user_id` (or anonymous). |
| **State machine** | Next state from current state + facts; missing facts; whether to run deductions; state/confidence descriptions. |
| **Governance engine** | LLM fact extraction from conversation; directive selection (priorities above); LLM response generation from directive + RAG + history. |
| **Risk rules** | Map facts → risk level, obligations list, warnings (including BLOCKED for prohibited). |
| **Obligation mapper** | Fact key ↔ obligation code; value classifiers (negative, positive, planned); **confidence scoring** (deterministic floor + threshold for verification). |
| **RAG** | TF-IDF + cosine similarity over `eu_ai_act_articles.json`; `query_by_topic`, `query_articles`, `identify_relevant_articles` for context in prompts. |
| **EU AI Act context** | Wraps RAG; `get_article_context_for_topic`, `get_article_context_for_query`; fallback to hardcoded excerpts if JSON missing. |
| **Dialogue memory** | `compute_topic_ask_count` (how many times each mandatory topic was asked), `compute_stuck_on_topic` (topic asked 2+ times still unresolved). |
| **High-risk checklist** | `get_missing_mandatory_topics`, `can_complete_high_risk_assessment` for HIGH-risk flow and report readiness. |
| **Report generator** | `create_compliance_cert(data)` → PDF bytes: cover, risk justification, obligation table, facts, recommendations, disclaimer. |
| **Database** | Persist projects, facts, obligations, interview logs, workflows, audit runs; migrations via SQLAlchemy `create_all`. |

### 6.3 Data Flow (One Chat Turn)

1. **Frontend** sends `POST /interview/chat` with `project_id`, `message`, optional `workflow_id`.
2. **Backend** loads project, facts (as dict), obligations, interview logs; validates ownership (or anonymous).
3. **Append** user message to `InterviewLog`.
4. **Governance engine** `extract_facts(history_text)` → LLM returns structured facts + `confidence_scores`; normalize compliance values; optional anti-manipulation downgrade (e.g. 2+ topics flipping to positive in one turn → set to partial_or_unclear).
5. **Hybrid confidence:** For each fact, `compute_fact_confidence(key, value)` gives deterministic score; final confidence = min(deterministic, LLM) if LLM provided, else deterministic; if same value re-extracted, keep max(new, existing). Persist to `Fact.confidence`.
6. **State machine** `determine_state(facts, current_state)` → next state; `get_missing_facts`; `calculate_confidence(facts)`.
7. **Risk rules** `evaluate_compliance_state(facts)` → risk_level, obligations list, warnings.
8. **Obligation creation/update:** If full evaluation state (CHECKPOINT/ASSESSMENT), create/update obligations from risk rules; **universal gap detection** updates obligation status from fact values (via obligation_mapper and status rules).
9. **Dialogue memory** `compute_topic_ask_count(logs)`, `compute_stuck_on_topic(...)`.
10. **Governance engine** `generate_next_question(...)` with facts, risk_level, state, obligations, topic_ask_count, stuck_on_topic, conversation_history, workflow_steps, **fact_confidences**:
    - Select directive (workflow, user-asked-about, verify low-confidence, Art. 14 block, sequential gap, report blocker, state-aware).
    - Optionally pull RAG context for the directive topic.
    - LLM generates natural-language reply from system prompt + directive + state + RAG + history.
11. **Append** bot message to `InterviewLog`; update project (interview_state, risk_level, compliance_status, etc.).
12. **Response** returns: `response`, `risk_level`, `facts`, `workflow_steps`, `obligations`, `state`, `confidence`, `state_description`, `compliance_status`, `terminated`.

---

## 7. Data Model and Database

**Database:** PostgreSQL (e.g. Neon); fallback SQLite for local dev. Connection uses `DATABASE_URL`; engine has `pool_pre_ping=True`, `pool_recycle=300`.

### 7.1 Tables

| Table | Purpose |
|-------|---------|
| **projects** | One row per assessment: id, user_id, name, description, created_at, updated_at, risk_level, status, interview_state, confidence_level, compliance_status. |
| **facts** | Key-value facts per project: project_id, key, value, confidence (0–100), source. Keys include domain, role, purpose, data_type, automation, context, human_oversight, data_governance, accuracy_robustness, record_keeping, transparency, workflow_steps (JSON string), etc. |
| **obligations** | Per-project obligations: project_id, code (e.g. ART_14_OVERSIGHT, ART_10), title, description, status (PENDING, MET, gap_detected, under_review, planned_remediation, etc.). |
| **interview_logs** | Chat history: project_id, workflow_id (nullable), sender (user/bot), message, timestamp. |
| **workflows** | Optional sub-flows per project: project_id, name, description, risk_level, created_at. |
| **audit_runs** | Technical (bias) audit runs: model, risk_level, score, details (JSON), user_id, system_prompt, timestamp. |

### 7.2 Important Conventions

- **workflow_steps** for a project are stored as a fact with key `workflow_steps` and value = JSON array of strings.
- **Obligation status** is updated from facts by universal gap detection (e.g. human_oversight → ART_14_OVERSIGHT; status derived from fact value and remediation flags).
- **user_id** on projects: Clerk user ID when authenticated; `null` or `"anonymous"` for unauthenticated; dashboard and project listing filter by current user.

---

## 8. Core Backend Logic

### 8.1 Files and Roles

| File | Role |
|------|------|
| **routers/interview.py** | Start interview, chat, list/get projects, generate report; anti-manipulation downgrade; workflow_steps detection; obligation loading; fact confidence persistence; calls engine and state machine. |
| **routers/audit.py** | Run bias test, get audit history. |
| **routers/workflow.py** | CRUD for workflows under a project. |
| **routers/dashboard.py** | GET /dashboard/stats: aggregate by user_id (summary, risk_distribution, obligation_breakdown, recent_projects, top_gaps, activity_timeline). |
| **core/engine.py** | GovernanceEngine: extract_facts, generate_next_question (directive selection, RAG, LLM reply). |
| **core/state_machine.py** | InterviewState, ConfidenceLevel, determine_state, get_missing_facts, should_run_deductions, is_full_evaluation_state, get_state_description, get_confidence_message. |
| **core/risk_rules.py** | evaluate_compliance_state(facts) → risk_level, obligations, warnings; Article 5 + Annex III + Article 50 logic. |
| **core/risk_logic.py** | Optional LLM risk pre-classification (OpenRouter GPT-3.5) for Technical Audit; returns risk_level, reasoning, metrics. |
| **core/obligation_mapper.py** | FACT_TO_OBLIGATION_MAP, OB_CODE_TO_TOPIC; get_obligation_code_for_fact, get_fact_key_for_obligation; is_negative_value, is_positive_value, is_planned_value; CONFIDENCE_THRESHOLD, compute_fact_confidence. |
| **core/high_risk_checklist.py** | HIGH_RISK_MANDATORY_TOPICS; get_missing_mandatory_topics; get_topic_question; can_complete_high_risk_assessment. |
| **core/dialogue_memory.py** | HIGH_RISK_TOPIC_ORDER, ARTICLE_PHRASES; compute_topic_ask_count; compute_stuck_on_topic. |
| **core/vector_store.py** | TF-IDF index over eu_ai_act_articles.json; query_articles, query_by_topic, identify_relevant_articles; tokenize, IDF, cosine similarity. |
| **core/eu_ai_act_context.py** | get_article_context_for_topic, get_article_context_for_query; fallback to hardcoded article excerpts. |
| **core/report_gen.py** | create_compliance_cert(data) → PDF: cover, risk justification, obligations table, facts, recommendations, disclaimer. |
| **core/auth.py** | get_user_id_optional(authorization), get_clerk_user_id(authorization) — JWT parsing for Clerk. |
| **database.py** | SQLAlchemy engine, Base, SessionLocal, init_db, get_db; models Project, Fact, Obligation, Workflow, InterviewLog, AuditRun. |

### 8.2 RAG and Ingest

- **ingest_eu_ai_act.py** — One-time script: writes structured EU AI Act article excerpts to `backend/eu_ai_act_articles.json` (used by the TF-IDF store). No ChromaDB; in-memory + JSON for compatibility and simplicity.
- **vector_store** — Loads JSON, builds TF-IDF over title+text, answers `query_articles(query, n)` and `query_by_topic(topic_key)`; `identify_relevant_articles(domain, purpose, workflow_steps)` for dynamic article selection at CHECKPOINT.

---

## 9. Frontend Structure

### 9.1 Tech Stack

- **React 19**, **Vite**, **TypeScript**
- **Tailwind CSS**, Shadcn-style components (Button, Card, Input, Textarea, Badge, Progress, ScrollArea, Tabs, etc.)
- **Clerk** — Authentication (SignedIn/SignedOut, UserButton, RedirectToSignIn)
- **React Router** — Routes and links
- **Axios** — HTTP client; base URL from `VITE_API_URL`
- **Recharts** — Dashboard charts (Pie, Bar, Area, etc.)
- **ReactMarkdown** — Bot message rendering (bold, lists, etc.)

### 9.2 Routes and Pages

| Route | Page | Purpose |
|-------|------|---------|
| `/` | Dashboard | KPIs (total/active/completed assessments, compliance rate, high-risk count); risk distribution pie; activity timeline; obligation status breakdown; top gaps; recent assessments table. Data from `DashboardService.getStats()`. |
| `/governance` | GovernanceChat | Compliance chat: create/select project, send messages, see workflow map and compliance sidebar; generate report button. Uses GovernanceService (startInterview, sendMessage, listProjects, getProject, generateReport). |
| `/audit` | AuditRun | Technical Audit: run bias/fairness test (model, risk level, persona); view history. Uses AuditService. |
| `/reports` | Reports | History & reports entry. |
| `/privacy` | PrivacyPolicy | Static privacy policy. |
| `/terms` | TermsOfUse | Static terms of use. |

### 9.3 API Service (api.ts)

- **AuditService:** analyzeRisk, runAudit, getHistory, downloadReport (calls compliance/risk-assessment, audit/run-bias-test, audit/history, compliance/generate-pdf).
- **GovernanceService:** startInterview, sendMessage, listProjects, getProject, generateReport (calls interview/start, interview/chat, interview/projects, interview/projects/:id, interview/projects/:id/generate-report).
- **DashboardService:** getStats (calls dashboard/stats).
- All authenticated requests use `getAuthHeaders(getToken)` (Clerk JWT in `Authorization: Bearer ...`).

---

## 10. Security, Guardrails, and Anti-Manipulation

- **CORS:** Backend allows all origins (configurable for production).
- **Auth:** Optional Clerk JWT; `get_user_id_optional` / `get_clerk_user_id`; project access restricted by user_id or anonymous.
- **Prohibited practices:** Article 5 logic in risk_rules; BLOCKED message and TERMINATED state; no compliance path for banned use cases.
- **Article 14 guardrail:** If human oversight is absent/no (and not yet remediation-accepted), a critical directive is generated (provider vs deployer wording); partial_or_unclear is handled in sequential gap handler, not as immediate block.
- **Anti-manipulation (extract_facts):** Prompt instructs to capture negative facts (absent/no); vague answers → partial_or_unclear; semantic evaluation of human oversight (informal “sometimes” → partial_or_unclear).
- **Anti-manipulation (post-extraction):** If 2+ compliance topics flip from unset/gap to positive in one turn, they are downgraded to partial_or_unclear and low confidence (e.g. 35).
- **Anti-manipulation (generate_next_question):** Rules in prompt: do not declare compliance on request; demand specific evidence; do not suggest report if gaps or partial_or_unclear remain.
- **Confidence:** Facts with confidence &lt; CONFIDENCE_THRESHOLD (70) trigger a verification directive (CHECKPOINT/ASSESSMENT only, one per turn); re-confirmation increases confidence so the loop closes.

---

## 11. Report Generation

- **Endpoint:** POST `/interview/projects/{project_id}/generate-report` (returns PDF binary).
- **Backend:** Builds `report_data` (model_tested, description, risk_level, compliance_score, compliance_status, interview_state, obligations, facts, workflow_steps, metric_breakdown); calls `create_compliance_cert(report_data)` from `core/report_gen.py`.
- **report_gen:** ReportLab PDF: cover (title, system name, date, disclaimer); risk classification and justification (Annex III/Article 5/50); obligation table (code, title, status, recommendation); facts summary; recommendations per topic when status ≠ MET; footer. Uses RAG/enriched context for obligation descriptions where applicable.

---

## 12. Deployment and Environment

- **Frontend:** Built with `npm run build` (Vite); output `dist/`. Deployed on **Netlify** (or Vercel): base directory `AI-Auditor/frontend`, build command `npm run build`, publish `dist`. Env vars: `VITE_API_URL`, `VITE_CLERK_PUBLISHABLE_KEY`. SPA redirect: all routes → index.html.
- **Backend:** Python 3.x (e.g. 3.12+); `uvicorn main:app --host 0.0.0.0 --port $PORT`. Deployed on **Railway** (or Render, Fly.io): root `AI-Auditor/backend`, start command as above. Env: `DATABASE_URL`, `OPENROUTER_API_KEY`, `CLERK_SECRET_KEY` (if used server-side), etc.
- **Database:** PostgreSQL (e.g. Neon); `DATABASE_URL` in backend env.
- **RAG:** Ensure `eu_ai_act_articles.json` is present (run `python ingest_eu_ai_act.py` once) or shipped with the backend; vector_store loads it at first use.

---

*End of document. For implementation details, refer to the source files under `backend/` and `frontend/`.*
