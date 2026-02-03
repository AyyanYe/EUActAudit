# PROJECT_CONTEXT.md

## AI Governance & EU AI Act Compliance Assistant – Canonical Spec

### 1. Project Overview

This project designs an AI governance and compliance assistant focused on the EU AI Act. It is not a generic chatbot, not a legal oracle, and not a thin wrapper around ChatGPT. The system is a structured compliance assessment platform that uses conversational AI as an interface to:

- Extract facts.
- Resolve ambiguity.
- Explain outcomes.

The core value is structure, consistency, traceability, and comparability—not raw intelligence.

---

### 2. What the system is not

The system does **not**:

- Certify legal compliance.
- Replace lawyers or auditors.
- Guarantee EU AI Act conformity.
- Make binding legal determinations.

Instead, it:

- Identifies likely risk categories.
- Maps legal obligations.
- Flags gaps and missing safeguards.
- Explains why a system is risky.
- Recommends mitigation actions.

---

### 3. Core Product Philosophy (Non-negotiable)

**Reframing:** This is not a chat that answers questions. It is a compliance state machine with a conversational interface.

Key principles:

1. **Determinism over intelligence**
   - Once facts are known, risk classification and obligations are rule-based.
2. **Explainability by design**
   - Every conclusion must be traceable to specific facts, explicit assumptions, and legal logic.
3. **Facts ≠ interpretations ≠ conclusions**
   - Store these separately at all times.
4. **Incompleteness is first-class**
   - “Unknown” is a valid state and must be preserved.
5. **Versioning matters**
   - Compliance is temporal and assessments evolve over time.

---

### 4. Why this is not “just ChatGPT”

ChatGPT alone:

- Has no persistent memory.
- Cannot enforce consistency.
- Cannot lock interpretations.
- Cannot produce audit-ready artifacts.
- Cannot compare systems across time or organizations.

This system:

- Maintains a single source of truth.
- Enforces structured decisions.
- Tracks unresolved obligations.
- Flags contradictions.
- Produces stable, repeatable outputs.

ChatGPT is an engine, not the product.

---

### 5. High-Level Architecture

Three layers:

1. **Compliance Data Model (core)**
   - Structured, persistent, deterministic.
2. **Conversational Interface**
   - Collects information, probes ambiguity, explains outcomes.
3. **Rule & Obligation Engine**
   - Classifies risk, maps EU AI Act obligations, identifies gaps.

---

### 6. Canonical Internal Data Model (AISystemProfile)

This represents one AI system.

#### 6.1 Metadata & Scope

- System name
- Organization
- Deployment regions
- Role (provider / deployer / both)
- B2B / B2C
- Lifecycle status (draft / assessed / updated)

#### 6.2 Intended Purpose & Context

- Primary function (e.g. candidate screening)
- Decision stage (advisory / pre-screen / final decision)
- Affected stakeholders
- Scale of use

> Intended purpose is legally central in the EU AI Act.

#### 6.3 Domain Classification (Fixed Taxonomy)

Examples:

- Employment & worker management
- Creditworthiness
- Education
- Healthcare
- Public services
- Law enforcement

Multiple domains allowed, but flagged.

#### 6.4 Automation & Human Control

- Fully automated? (yes/no/unknown)
- Human-in-the-loop?
- Override capability?
- Are human decisions binding?

#### 6.5 Data & Model Characteristics (High-level)

- Personal data used?
- Special category data?
- Training data source (internal / third-party / mixed)
- Continuous learning?

#### 6.6 Fundamental Rights Impact

For each:

- Non-discrimination
- Privacy & data protection
- Access to services
- Due process

Store:

- Impact likelihood (low/medium/high/unknown)
- Rationale (text)

#### 6.7 Risk Classification (Derived, Not User-Entered)

- Risk category: Unacceptable / High-risk / Limited risk / Minimal risk
- Confidence level
- Triggering conditions (linked to facts)

#### 6.8 Applicable EU AI Act Obligations

Mapped deterministically based on:

- Risk category
- Domain
- Role (provider/deployer)

Each obligation includes:

- Description
- Legal basis (article / annex)
- Status (met / unmet / unknown)
- Evidence placeholder

#### 6.9 Gaps & Mitigation Actions

For each unmet obligation:

- Risk description
- Recommended mitigation
- Priority
- Dependencies

#### 6.10 Audit Trail & Reasoning Log

- What changed
- Why
- Based on which user input
- Timestamp

---

### 7. Risk Taxonomy (Conceptual)

Risk is evaluated across multiple dimensions, not a single score.

Core dimensions:

1. Domain (employment, credit, etc.)
2. Impact level (informational → automated decision)
3. Rights affected
4. Level of human control
5. Scale & reach

High-risk classification is rule-triggered, not subjective.

---

### 8. Conversation Design (How chat is used)

Chat is not the source of truth. Workflow:

1. System asks targeted questions.
2. User answers in natural language.
3. AI extracts structured facts.
4. Facts update the data model.
5. Rules re-run.
6. Changes are explained to the user.

The system progressively deepens understanding instead of asking everything upfront.

---

### 9. User Journey (High-level)

1. **Initial intake**
   - Business context, AI system purpose, geography & role.
2. **Preliminary risk hypothesis**
   - “This may fall under High-Risk AI; more info needed.”
3. **Progressive clarification**
   - Automation, data usage, human oversight, rights impact.
4. **Risk classification checkpoint**
   - Summary, confidence, open questions.
5. **Obligation mapping**
   - What applies, what’s missing, why it matters.
6. **Mitigation recommendations**
   - Concrete, actionable steps.

---

### 10. Testing Philosophy

The system is tested for:

- Consistency (same facts → same outcome)
- Escalation (risk increases when harmful details emerge)
- Overconfidence avoidance
- Explanation quality
- Stability across reworded inputs

Not just numerical accuracy.

---

### 11. Use Case Example (HR / Employment)

AI used to screen or rank candidates:

- Employment domain
- Impact on access to work
- Potential discrimination risk

Likely classification:

- High-Risk AI system (Annex III)

Key obligations surfaced:

- Bias mitigation
- Data governance
- Human oversight
- Transparency to candidates
- Logging & traceability

Even if “only recommendations.”

---

### 12. What this project demonstrates

- Systems thinking
- Regulatory reasoning
- AI governance design
- Separation of intelligence from control
- Responsible AI principles

This is design and architecture, not just prompting.

---

### 13. Explicit limitations

- Not legal advice
- Not compliance certification
- Interpretive uncertainty acknowledged
- Depends on user-provided information

---

### 14. Final One-Sentence Definition

> A structured, conversational AI governance system that builds a persistent compliance profile for AI systems and maps EU AI Act risks, obligations, and mitigation actions in an explainable, auditable way.
