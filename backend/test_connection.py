# backend/test_connection.py
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

def test_db():
    database_url = os.getenv("DATABASE_URL", "sqlite:///./eu_ai_act_2025.db")
    print(f"[*] Testing connection to: {database_url}")
    
    # SQLite vs PostgreSQL configurations
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        
    try:
        engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)
        # Try to connect
        with engine.connect() as conn:
            print("[+] Database connection successful!")
    except Exception as e:
        print(f"[-] Database connection failed: {e}")
        if not database_url.startswith("sqlite"):
            print("[!] Suggestion: Comment out DATABASE_URL in your backend/.env to fall back to local SQLite.")

def test_keys():
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    clerk_key = os.getenv("CLERK_SECRET_KEY")
    
    if openrouter_key and not openrouter_key.startswith("your_"):
        print("[+] OpenRouter API Key is set.")
    else:
        print("[-] OpenRouter API Key is missing or using placeholder.")
        
    if clerk_key and not clerk_key.startswith("your_"):
        print("[+] Clerk Secret Key is set.")
    else:
        print("[-] Clerk Secret Key is missing or using placeholder.")

if __name__ == "__main__":
    print("=== EU AI Act Governance System Connection Checker ===")
    test_db()
    test_keys()
