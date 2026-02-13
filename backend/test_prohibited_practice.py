"""
Test script to verify prohibited practice detection and exemption probe.
Tests the emotion recognition in education scenario.
"""
import requests
import json
import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

API_URL = "http://localhost:8000"

def test_emotion_recognition_ban():
    """Test the emotion recognition prohibition flow."""
    
    print("=" * 70)
    print("Testing Prohibited Practice: Emotion Recognition in Education")
    print("=" * 70)
    
    # Step 1: Start interview
    print("\n[1] Starting interview...")
    response = requests.post(f"{API_URL}/interview/start", json={
        "name": "Student Engagement Monitor",
        "description": "AI system to monitor student engagement and detect boredom in classrooms."
    })
    data = response.json()
    project_id = data["project_id"]
    print(f"[OK] Project created: ID {project_id}")
    print(f"Bot: {data['message']}")
    
    # Step 2: User describes emotion recognition system
    print("\n[2] User: We monitor student boredom using facial expression analysis to detect when students are disengaged.")
    response = requests.post(f"{API_URL}/interview/chat", json={
        "project_id": project_id,
        "message": "We monitor student boredom using facial expression analysis to detect when students are disengaged."
    })
    data = response.json()
    print(f"\nBot: {data['response']}")
    print(f"Facts extracted: {json.dumps(data['facts'], indent=2)}")
    print(f"Risk Level: {data['risk_level']}")
    print(f"State: {data.get('state', 'N/A')}")
    
    # Check if emotion_recognition was detected
    if data.get("facts", {}).get("purpose") == "emotion_recognition":
        print("\n[SUCCESS] 'emotion_recognition' purpose was correctly extracted")
    else:
        print(f"\n[FAILURE] Purpose was '{data.get('facts', {}).get('purpose', 'NOT FOUND')}' (expected 'emotion_recognition')")
    
    # Check if PENDING_PROHIBITED or exemption probe question was asked
    risk_level = data.get("risk_level", "")
    response_text = data.get("response", "").lower()
    
    if risk_level == "PENDING_PROHIBITED" or "wait" in response_text or "banned" in response_text or "article 5" in response_text:
        print("\n[SUCCESS] Exemption probe question was triggered")
        if "medical" in response_text or "safety" in response_text:
            print("[SUCCESS] Exemption probe mentions medical/safety purpose")
    else:
        print(f"\n[FAILURE] Exemption probe was NOT triggered. Risk level: {risk_level}")
    
    # Step 3: User answers "No" to exemption (just for engagement/grades)
    print("\n[3] User: No, just for engagement and grades.")
    response = requests.post(f"{API_URL}/interview/chat", json={
        "project_id": project_id,
        "message": "No, just for engagement and grades."
    })
    data = response.json()
    print(f"\n{'='*70}")
    print("CRITICAL TEST: After user says 'No' to exemption")
    print(f"{'='*70}")
    print(f"Bot Response: {data['response']}")
    print(f"\nFacts extracted: {json.dumps(data['facts'], indent=2)}")
    print(f"Risk Level: {data['risk_level']}")
    print(f"Obligations: {data.get('obligations', [])}")
    print(f"State: {data.get('state', 'N/A')}")
    
    # Check if UNACCEPTABLE was set
    if data.get("risk_level") == "UNACCEPTABLE":
        print("\n[SUCCESS] Risk level correctly set to UNACCEPTABLE")
    else:
        print(f"\n[FAILURE] Risk level is '{data.get('risk_level')}' (expected UNACCEPTABLE)")
    
    # Check if exemption_probe_answered was captured
    if data.get("facts", {}).get("exemption_probe_answered") == "no":
        print("[SUCCESS] 'exemption_probe_answered' was correctly extracted as 'no'")
    else:
        print(f"[WARNING] 'exemption_probe_answered' is '{data.get('facts', {}).get('exemption_probe_answered', 'NOT FOUND')}'")
    
    # Check if bot stopped asking compliance questions
    response_text = data.get("response", "").lower()
    if "assessment halted" in response_text or "cannot proceed" in response_text or "illegal" in response_text:
        print("[SUCCESS] Bot issued prohibited practice block message")
    else:
        print("[WARNING] Bot may still be asking compliance questions instead of blocking")
    
    # Check if bot is NOT asking about human oversight or data
    if "human oversight" in response_text or "data" in response_text or "compliance" in response_text:
        if "cannot" in response_text or "halted" in response_text or "illegal" in response_text:
            print("[SUCCESS] Bot is blocking, not asking compliance questions")
        else:
            print("[FAILURE] Bot is still asking compliance questions after UNACCEPTABLE determination")
    else:
        print("[SUCCESS] Bot is NOT asking compliance questions")
    
    print("\n" + "=" * 70)
    print("Test Complete")
    print("=" * 70)

if __name__ == "__main__":
    try:
        test_emotion_recognition_ban()
    except Exception as e:
        print(f"\n[ERROR] Error during test: {e}")
        import traceback
        traceback.print_exc()

