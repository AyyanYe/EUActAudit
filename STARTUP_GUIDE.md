# Startup Guide - AuditGenius

## Prerequisites Check ✅

- ✅ Python 3.14.3 installed (use `py` command)
- ✅ Node.js v22.11.0 installed
- ✅ npm 10.9.1 installed

## Backend Setup

### 1. Navigate to Backend Directory
```powershell
cd F:\AI_Genius\AI-Auditor\backend
```

### 2. Set Up Virtual Environment & Install Dependencies
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Variables
Make sure you have a `.env` file in the `backend` directory with:
```
OPENROUTER_API_KEY=your_key_here
```

### 4. Start Backend Server
Ensure your virtual environment is activated, then run:
```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at: **http://localhost:8000**
API Documentation: **http://localhost:8000/docs**

## Frontend Setup

### 1. Navigate to Frontend Directory
```powershell
cd F:\AI_Genius\AI-Auditor\frontend
```

### 2. Install Dependencies (if not already done)
```powershell
npm install
```

### 3. Environment Variables
Create a `.env` file in the `frontend` directory with:
```
VITE_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key_here
VITE_API_URL=http://localhost:8000
```

**Note:** You need a Clerk account to get the publishable key. Sign up at https://clerk.com

### 4. Start Frontend Development Server
```powershell
npm run dev
```

The frontend will be available at: **http://localhost:5173**

## Troubleshooting

### Backend Issues
- **Port 8000 already in use**: Change the port in the uvicorn command: `--port 8001`
- **Module not found**: Make sure your virtual environment is activated (`.\venv\Scripts\activate`) and run `pip install -r requirements.txt`
- **Database errors**: The database will be created automatically on first run

### Frontend Issues
- **Clerk authentication error**: Make sure `VITE_CLERK_PUBLISHABLE_KEY` is set in `.env`
- **API connection error**: Check that backend is running and `VITE_API_URL` points to the correct backend URL
- **Port 5173 already in use**: Vite will automatically use the next available port

## Quick Start (Both Servers)

Open two terminal windows:

**Terminal 1 - Backend:**
```powershell
cd F:\AI_Genius\AI-Auditor\backend
.\venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```powershell
cd F:\AI_Genius\AI-Auditor\frontend
npm run dev
```

Then open your browser to: **http://localhost:5173**

## State Machine Features

The system now includes a deterministic state machine:
- **INIT** → **INTAKE** → **DISCOVERY** → **CHECKPOINT** → **ASSESSMENT**
- Confidence levels: LOW, MEDIUM, HIGH
- State-aware question generation
- Real-time dashboard updates

Enjoy building! 🚀

