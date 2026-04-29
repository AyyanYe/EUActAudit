# 🇪🇺 AuditGenius: EU AI Act Compliance Auditor

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/react-18.x-61dafb.svg)](https://reactjs.org/)

AuditGenius is a comprehensive, open-source AI Governance and Compliance Auditing System designed to evaluate AI models (LLMs) against the strict requirements of the 2025 EU AI Act. 

It uses an advanced **Hybrid Evaluation Engine** that combines deterministic mathematical formulas with LLM-based "Judge" evaluations to scientifically highlight key compliance issues in your workflow and provide actionable advice on how to fix them, ensuring your AI systems are safe, ethical, and legally compliant.

---

##  Documentation Directory

To keep this repository clean and organized, our documentation is split into specific guides. Please refer to the documents below for detailed information:

- **[Startup Guide & Installation](STARTUP_GUIDE.md):** Step-by-step instructions for running the frontend and backend locally.
- **[Project Architecture & Explanation](PROJECT_EXPLANATION.md):** Deep dive into how the Hybrid Engine, State Machine, and Database interact.
- **[Project Context & Goals](PROJECT_CONTEXT.md):** Understand the vision, the EU AI Act alignment, and the problem this software solves.
- **[Clerk Authentication Setup](CLERK_SETUP.md):** Instructions for configuring the Clerk auth system for the frontend.
- **[Contributing Guidelines](CONTRIBUTING.md):** Read this before making a Pull Request! Includes our Code of Conduct and branching rules.

---

## Key Capabilities

1. **Automated Risk Assessment:** Classifies use cases (High, Limited, Minimal Risk) based on Annex III of the EU AI Act.
2. **Deterministic State Machine Intake:** Guides users through INIT → INTAKE → DISCOVERY → CHECKPOINT → ASSESSMENT to gather project facts.
3. **Counterfactual Testing:** Generates pairs of prompts (e.g., "Resume for John" vs. "Resume for Jane") to trap models into revealing hidden biases.
4. **Actionable Compliance Insights:** Rather than generating arbitrary "compliance scores", the Hybrid Engine highlights specific compliance gaps in your workflow and provides actionable, step-by-step advice on how to fix them.
5. **Multi-Model Support:** Capable of auditing targets via OpenRouter (GPT-4o, Claude 3, Gemini, etc.).
6. **Evidence Recording:** Stores detailed logs in SQLite/PostgreSQL and generates downloadable PDF Compliance Certificates.

---

## Technical Stack

- **Frontend:** React (Vite), TypeScript, Tailwind CSS, Shadcn/UI, Recharts.
- **Backend:** FastAPI (Python), SQLAlchemy, LangChain.
- **AI Orchestration:** OpenRouter, OpenAI.
- **Math/NLP:** NumPy, SciPy, TextBlob.

---

## Credits & Acknowledgements

**Author & Maintainer:** Ayyan Ahmed

This software originally started as a course project at **TU Darmstadt**, Germany, developed under the supervision of [Agoston Torok](https://github.com/agostontorok). It has since been expanded and open-sourced to provide free compliance tools for the global developer community. 

---

*For support, feature requests, or bug reports, please open an Issue on GitHub.*
