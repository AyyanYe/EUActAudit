# backend/core/risk_rules.py

def evaluate_compliance_state(facts: dict):
    """
    The Deterministic Rule Engine for EU AI Act (2025 Version).
    Input: Dictionary of facts (e.g. {'domain': 'recruitment', 'role': 'provider'})
    Output: Risk Level, List of Obligations, Warnings
    """
    
    risk_level = "MINIMAL" # Default
    obligations = []
    warnings = []
    
    # --- LEVEL 1: UNACCEPTABLE RISK (BANS - Article 5) ---
    # Effective Feb 2, 2025
    
    if facts.get("purpose") == "social_scoring":
        return "UNACCEPTABLE", ["BANNED: Social scoring is prohibited under Art 5."], ["STOP: This system cannot be legally deployed."]

    if facts.get("purpose") == "emotion_recognition" and facts.get("context") in ["workplace", "education"]:
        return "UNACCEPTABLE", ["BANNED: Emotion recognition in work/schools is prohibited."], ["STOP: Change the use case immediately."]
        
    if facts.get("purpose") == "biometric_id" and facts.get("biometric_mode") == "real_time" and facts.get("context") == "public_space":
        # Exception logic could go here, but default to ban for MVP
        return "UNACCEPTABLE", ["BANNED: Real-time remote biometric ID in public spaces."], ["STOP: Only law enforcement with judicial auth can do this."]

    # --- LEVEL 2: HIGH RISK (Annex III) ---
    # Effective Aug 2026, but companies prepare now
    
    high_risk_domains = [
        "recruitment", "hr", "worker_management",  # Annex III (4)
        "education", "vocational_training",        # Annex III (3)
        "critical_infrastructure",                 # Annex III (2)
        "credit_scoring", "insurance",             # Annex III (5) - Essential Services
        "biometrics",                              # Annex III (1) - Post-remote ID
        "law_enforcement", "migration", "justice"  # Annex III (6,7,8)
    ]
    
    if facts.get("domain") in high_risk_domains:
        risk_level = "HIGH"
        
        # Determine Role-Based Obligations (Provider vs Deployer)
        role = facts.get("role", "unknown").lower()
        
        if role == "provider" or role == "builder":
            obligations.extend([
                {"code": "ART_16", "title": "Quality Management System", "desc": "Implement a QMS compliant with Art 17."},
                {"code": "ART_43", "title": "Conformity Assessment", "desc": "Must undergo conformity assessment before deployment."},
                {"code": "ART_10", "title": "Data Governance", "desc": "Training data must be relevant, representative, and free of errors."}
            ])
        elif role == "deployer" or role == "user":
            obligations.extend([
                {"code": "ART_26", "title": "Human Oversight", "desc": "Ensure human overseers are trained and have authority to stop the system."},
                {"code": "ART_26_LOGS", "title": "Monitoring & Logging", "desc": "Keep logs of operation for at least 6 months."}
            ])
        else:
            warnings.append("Role unclear: Are you building this (Provider) or buying it (Deployer)?")

    # --- LEVEL 3: LIMITED RISK (Transparency - Art 50) ---
    
    elif facts.get("capability") == "chatbot" or facts.get("capability") == "interaction":
        risk_level = "LIMITED"
        obligations.append({"code": "ART_50", "title": "Transparency Notification", "desc": "Users must be informed they are talking to an AI."})
        
    elif facts.get("capability") == "content_generation" and facts.get("media_type") in ["image", "video", "audio"]:
        risk_level = "LIMITED"
        obligations.append({"code": "ART_50_WATERMARK", "title": "AI Watermarking", "desc": "Output must be machine-readable as AI generated."})

    return risk_level, obligations, warnings