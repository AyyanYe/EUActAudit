"""
Test script to verify the conversation loop fix.
Simulates the problematic conversation to ensure negative facts are captured.
"""
import asyncio
import requests
import json
import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

API_URL = "http://localhost:8000"

def test_conversation():
    """Test the conversation flow that was causing loops."""
    
    print("=" * 60)
    print("Testing Conversation Flow - Loop Fix Verification")
    print("=" * 60)
    
    # Step 1: Start interview
    print("\n[1] Starting interview...")
    response = requests.post(f"{API_URL}/interview/start", json={
        "name": "TalentRanker AI",
        "description": "An automated screening system that parses candidate resumes to score and rank applicants based on their fit for job descriptions."
    })
    data = response.json()
    project_id = data["project_id"]
    print(f"[OK] Project created: ID {project_id}")
    print(f"Bot: {data['message']}")
    
    # Step 2: User describes the system
    print("\n[2] User: We are using this system to automatically filter out low-scoring candidates based on their CVs before a human recruiter sees them. The model was trained by an external vendor, and we are just deploying it internally for our HR department.")
    response = requests.post(f"{API_URL}/interview/chat", json={
        "project_id": project_id,
        "message": "We are using this system to automatically filter out low-scoring candidates based on their CVs before a human recruiter sees them. The model was trained by an external vendor, and we are just deploying it internally for our HR department."
    })
    data = response.json()
    print(f"Bot: {data['response']}")
    print(f"Facts extracted: {json.dumps(data['facts'], indent=2)}")
    print(f"Risk Level: {data['risk_level']}")
    
    # Step 3: User mentions special category data
    print("\n[3] User: Yes, the resumes contain names and addresses which could indirectly reveal ethnic origin. Additionally, we voluntarily collect information about candidate disabilities to provide accommodations during the interview process.")
    response = requests.post(f"{API_URL}/interview/chat", json={
        "project_id": project_id,
        "message": "Yes, the resumes contain names and addresses which could indirectly reveal ethnic origin. Additionally, we voluntarily collect information about candidate disabilities to provide accommodations during the interview process."
    })
    data = response.json()
    print(f"Bot: {data['response']}")
    print(f"Facts extracted: {json.dumps(data['facts'], indent=2)}")
    
    # Step 4: User says NO human oversight (THIS WAS CAUSING THE LOOP)
    print("\n[4] User: Currently, the process is fully automated to save time. The system automatically sends a rejection email to any candidate who scores below 75%. We do not have a human reviewing these specific decisions because we receive thousands of applications.")
    response = requests.post(f"{API_URL}/interview/chat", json={
        "project_id": project_id,
        "message": "Currently, the process is fully automated to save time. The system automatically sends a rejection email to any candidate who scores below 75%. We do not have a human reviewing these specific decisions because we receive thousands of applications."
    })
    data = response.json()
    print(f"\n{'='*60}")
    print("CRITICAL TEST: After user says 'no human oversight'")
    print(f"{'='*60}")
    print(f"Bot Response: {data['response']}")
    print(f"\nFacts extracted: {json.dumps(data['facts'], indent=2)}")
    print(f"Risk Level: {data['risk_level']}")
    print(f"Obligations: {data['obligations']}")
    print(f"State: {data.get('state', 'N/A')}")
    print(f"Confidence: {data.get('confidence', 'N/A')}")
    
    # Check if human_oversight was captured
    if "human_oversight" in data.get("facts", {}):
        oversight_value = data["facts"]["human_oversight"]
        if oversight_value == "no":
            print(f"\n[SUCCESS] 'human_oversight' was correctly extracted as 'no'")
        else:
            print(f"\n[WARNING] 'human_oversight' extracted as '{oversight_value}' (expected 'no')")
    else:
        print(f"\n[FAILURE] 'human_oversight' was NOT extracted from the conversation")
    
    # Step 5: Check if bot asks about human oversight again (should NOT)
    print("\n[5] Checking if bot loops by asking about human oversight again...")
    response = requests.post(f"{API_URL}/interview/chat", json={
        "project_id": project_id,
        "message": "That's all the information I have."
    })
    data = response.json()
    print(f"Bot: {data['response']}")
    
    # Check if response contains questions about human oversight
    response_lower = data['response'].lower()
    if "human oversight" in response_lower or "human review" in response_lower:
        if "compliance gap" in response_lower or "critical" in response_lower or "article 14" in response_lower:
            print("\n[SUCCESS] Bot is addressing compliance gap, not asking again")
        else:
            print("\n[FAILURE] Bot is asking about human oversight again (LOOP DETECTED)")
    else:
        print("\n[SUCCESS] Bot is NOT asking about human oversight again")
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_conversation()
    except Exception as e:
        print(f"\n[ERROR] Error during test: {e}")
        import traceback
        traceback.print_exc()

