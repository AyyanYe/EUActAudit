### PROJECT OVERVIEW
----------------
AuditGenius is a comprehensive AI Compliance Auditing System designed to evaluate 
AI models (LLMs) against the requirements of the EU AI Act. It uses a "Hybrid 
Evaluation Engine" that combines deterministic mathematical formulas with 
LLM-based judging to scientifically measure bias, fairness, and transparency.

Key Capabilities:
1. Automated Risk Assessment: Classifies use cases (High, Limited, Minimal Risk)
   based on Annex III of the EU AI Act.
2. Counterfactual Testing: Generates pairs of prompts (e.g., "Resume for John" 
   vs. "Resume for Jane") to trap models into revealing bias.
3. Hybrid Scoring System: Calculates compliance scores using a weighted average:
   - 50% Mathematical Analysis (Cosine Similarity, Sentiment, Length Ratios).
   - 50% AI "Judge" Evaluation (GPT-4 grading the fairness).
4. Multi-Model Support: Capable of auditing GPT-3.5, GPT-4, Claude 3, and 
   Gemini 1.5 Pro.
5. Evidence Recording: Stores detailed logs in SQLite and generates PDF 
   Compliance Certificates.

------------------------------------------------------------------------------
TECHNICAL STACK
----------------
[Frontend]
- Framework: React (Vite) + TypeScript
- Styling: Tailwind CSS
- Components: Shadcn/UI
- Visualization: Recharts

[Backend]
- Framework: FastAPI (Python)
- Database: SQLite
- AI Orchestration: LangChain
- Math/NLP: NumPy, SciPy, TextBlob
- PDF Generation: ReportLab

------------------------------------------------------------------------------
PREREQUISITES
----------------
1. Node.js (v18+)
2. Python (v3.10+)
3. API Keys (at least one required):
   - OpenAI API Key (Required for the "Judge" and Embeddings)
   - Anthropic API Key (Optional, for auditing Claude)
   - Google Gemini API Key (Optional, for auditing Gemini)

------------------------------------------------------------------------------
INSTALLATION & SETUP
----------------

STEP 1: BACKEND SETUP
1. Open a terminal and navigate to the backend folder:
   $ cd backend

2. Create and activate a virtual environment (optional but recommended):
   $ python -m venv venv
   $ source venv/bin/activate  (On Windows: venv\Scripts\activate)

3. Install dependencies:
   $ pip install fastapi uvicorn openai langchain-openai langchain-anthropic \
     langchain-google-genai python-multipart reportlab numpy scipy textblob requests

4. Download NLP corpora for TextBlob:
   $ python -m textblob.download_corpora

5. Start the server:
   $ uvicorn main:app --reload

   > Server will run at: http://localhost:8000
   > API Documentation: http://localhost:8000/docs

STEP 2: FRONTEND SETUP
1. Open a new terminal and navigate to the frontend folder:
   $ cd frontend

2. Install dependencies:
   $ npm install

3. Configure the API URL (Crucial for Cloud IDEs like Codespaces):
   - Open `src/services/api.ts`
   - If running locally: Ensure API_URL is 'http://localhost:8000'
   - If on Codespaces: Copy your Public Backend Port URL (no trailing slash).

4. Start the application:
   $ npm run dev

   > Application will run at: http://localhost:5173

------------------------------------------------------------------------------
HOW TO RUN AN AUDIT
----------------
1. Open the Dashboard (http://localhost:5173).
2. Click "Run Audit" in the sidebar.
3. Step 1: Configuration
   - Enter a system description (e.g., "A loan approval AI...").
   - Type metrics to test (e.g., "Gender Bias", "Socioeconomic Bias").
   - Select the Target Model (e.g., GPT-3.5-Turbo).
   - Enter your API Key for that model.
4. Click "Analyze Risk". The system will auto-determine the Risk Level.
5. Click "Start Audit".
6. Wait for the "Hybrid Evaluation" to finish (check backend logs for progress).
7. View the results on the Dashboard and download the PDF Report.

------------------------------------------------------------------------------
PROJECT STRUCTURE
----------------
```
/backend
  /core
    - risk_logic.py       # Logic for EU AI Act categorization
    - evaluation_engine.py# The Hybrid Engine (Generates pairs, runs tests)
  /routers
    - audit.py            # API endpoints for running tests
    - compliance.py       # API endpoints for risk assessment
  /utils
    - math_evaluator.py   # Math formulas (Cosine sim, Sentiment, etc.)
  - database.py           # SQLite connection and schema
  - main.py               # FastAPI entry point

/frontend
  /src
    /components           # Shadcn UI components
    /pages
      - Dashboard.tsx     # Main stats view
      - AuditRun.tsx      # The Audit Wizard
      - Reports.tsx       # Historical data table
    /services
      - api.ts            # Axios configuration
    - App.tsx             # Routing
```

------------------------------------------------------------------------------
TROUBLESHOOTING
----------------
1. "Connection Refused" / Network Errors:
   - Ensure the Backend terminal is running.
   - If using GitHub Codespaces, ensure Port 8000 visibility is set to PUBLIC.
   - Check `frontend/src/services/api.ts` for trailing slashes in the URL.

2. "Module Not Found":
   - Ensure you installed the new math libraries in the backend:
     `pip install numpy scipy textblob`

3. "Model Not Found" / API Errors:
   - Ensure you selected the correct model in the dropdown.
   - Verify the API Key corresponds to the provider (e.g., don't use an OpenAI 
     key for Claude).

==============================================================================
