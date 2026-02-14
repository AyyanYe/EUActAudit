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
    
    # Check for prohibited practices with exemption probe logic
    is_prohibited_emotion_recognition = (
        facts.get("purpose") == "emotion_recognition" and 
        facts.get("context") in ["workplace", "education", "school"]
    )
    
    is_prohibited_social_scoring = facts.get("purpose") == "social_scoring"
    
    is_prohibited_biometric = (
        facts.get("purpose") == "biometric_id" and 
        facts.get("biometric_mode") == "real_time" and 
        facts.get("context") == "public_space"
    )
    
    # If prohibited practice detected, check if exemption probe has been answered
    if is_prohibited_emotion_recognition or is_prohibited_social_scoring or is_prohibited_biometric:
        exemption_answered = facts.get("exemption_probe_answered")
        
        # If exemption probe not yet asked, return PENDING status (will trigger probe question)
        if exemption_answered is None:
            if is_prohibited_emotion_recognition:
                return "PENDING_PROHIBITED", [], ["EXEMPTION_PROBE_NEEDED: Emotion recognition in education/workplace requires exemption check."]
            elif is_prohibited_social_scoring:
                return "PENDING_PROHIBITED", [], ["EXEMPTION_PROBE_NEEDED: Social scoring requires exemption check."]
            elif is_prohibited_biometric:
                return "PENDING_PROHIBITED", [], ["EXEMPTION_PROBE_NEEDED: Real-time biometric ID requires exemption check."]
        
        # If exemption probe answered "no" (no medical/safety exemption), then it's UNACCEPTABLE
        if exemption_answered == "no":
            if is_prohibited_emotion_recognition:
                context_type = "school" if facts.get("context") in ["education", "school"] else "workplace"
                return "UNACCEPTABLE", [
                    "BANNED: Emotion recognition in education/workplace is prohibited under Article 5."
                ], [
                    f"BLOCKED: This use case is illegal in the EU under Article 5 due to the use of emotion recognition in a {context_type} context. I cannot proceed with generating a compliance profile for a banned use case."
                ]
            elif is_prohibited_social_scoring:
                return "UNACCEPTABLE", [
                    "BANNED: Social scoring is prohibited under Article 5."
                ], [
                    "BLOCKED: This use case is illegal in the EU under Article 5 due to the use of social scoring. Article 5 prohibits social scoring systems per se (inherently illegal). I cannot proceed with generating a compliance profile for a banned use case."
                ]
            elif is_prohibited_biometric:
                return "UNACCEPTABLE", [
                    "BANNED: Real-time remote biometric ID in public spaces is prohibited under Article 5."
                ], [
                    "BLOCKED: This use case is illegal in the EU under Article 5 due to the use of real-time remote biometric identification in public spaces. Article 5 prohibits this practice per se (inherently illegal), except for law enforcement with judicial authorization. I cannot proceed with generating a compliance profile for a banned use case."
                ]
        
        # If exemption probe answered "yes" (has medical/safety exemption), treat as HIGH RISK instead
        # (The system may be allowed but requires strict compliance)
        if exemption_answered == "yes":
            # Fall through to HIGH RISK evaluation below
            # Note: Even with exemption, emotion recognition in education is still HIGH RISK
            pass

    # --- LEVEL 2: HIGH RISK (Annex III) ---
    # Effective Aug 2026, but companies prepare now
    
    # Skip HIGH RISK evaluation if we already determined UNACCEPTABLE
    if risk_level == "UNACCEPTABLE":
        return risk_level, obligations, warnings
    
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
        
        # Common obligations for ALL high-risk systems (both provider and deployer)
        obligations.extend([
            {"code": "ART_15", "title": "Accuracy & Robustness", "desc": "System must meet accuracy, robustness, and cybersecurity requirements under Article 15."},
            {"code": "ART_12", "title": "Record Keeping", "desc": "System must automatically log operations and decisions under Article 12."},
        ])
        
        if role == "provider" or role == "builder":
            obligations.extend([
                {"code": "ART_16", "title": "Quality Management System", "desc": "Implement a QMS compliant with Art 17."},
                {"code": "ART_43", "title": "Conformity Assessment", "desc": "Must undergo conformity assessment before deployment."},
                {"code": "ART_10", "title": "Data Governance", "desc": "Training data must be relevant, representative, and free of errors."},
            ])
            # Providers must DESIGN systems with human oversight capability (Article 14).
            if facts.get("human_oversight") in ["no", "absent", "partial"] or facts.get("automation") == "fully_automated":
                warnings.append("Article 14: Providers must design high-risk systems to allow effective human oversight by deployers.")
                obligations.append({
                    "code": "ART_14_OVERSIGHT", 
                    "title": "Human Oversight by Design", 
                    "desc": "Providers must design the system so deployers can implement effective human oversight — including the ability to override or halt AI decisions."
                })
        elif role == "deployer" or role == "user":
            obligations.extend([
                {"code": "ART_26", "title": "Human Oversight", "desc": "Ensure human overseers are trained and have authority to stop the system."},
                {"code": "ART_26_LOGS", "title": "Monitoring & Logging", "desc": "Keep logs of operation for at least 6 months."},
                {"code": "ART_10", "title": "Data Governance", "desc": "Input data must be relevant and representative for the system's intended purpose."},
            ])
            
            # Check for missing or insufficient human oversight (critical compliance gap). Article 14: "partial" and "absent" are non-compliant.
            if facts.get("human_oversight") in ["no", "absent", "partial"] or facts.get("automation") == "fully_automated":
                warnings.append("CRITICAL: Article 14 requires human oversight for high-risk systems. Fully automated decisions without human review are non-compliant.")
                obligations.append({
                    "code": "ART_14_OVERSIGHT", 
                    "title": "Mandatory Human Oversight", 
                    "desc": "High-risk systems MUST have human oversight. You cannot rely solely on automated rejections. Add human review step for all decisions."
                })
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