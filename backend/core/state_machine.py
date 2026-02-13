# backend/core/state_machine.py
"""
Deterministic State Machine for Governance Interview Process.

States: INIT → INTAKE → DISCOVERY → CHECKPOINT → ASSESSMENT

Each state has:
- Entry conditions
- Required facts to collect
- Exit conditions (what moves to next state)
- What deductions run at this state
"""

from typing import Dict, List, Tuple, Optional
from enum import Enum

class InterviewState(str, Enum):
    """The five states of the interview process."""
    INIT = "INIT"                    # Project created, no facts yet
    INTAKE = "INTAKE"                # Gathering core facts (domain, role, purpose)
    DISCOVERY = "DISCOVERY"          # Deep dive (data types, automation, context)
    CHECKPOINT = "CHECKPOINT"        # Running risk rules, checking completeness
    ASSESSMENT = "ASSESSMENT"        # Final state, obligations identified

class ConfidenceLevel(str, Enum):
    """Confidence in the current classification."""
    LOW = "LOW"          # < 3 key conditions met
    MEDIUM = "MEDIUM"     # 3-4 key conditions met
    HIGH = "HIGH"         # 5+ key conditions met

class StateMachine:
    """
    Manages state transitions and determines what to ask next.
    """
    
    # Critical facts required for each state
    INTAKE_REQUIRED = ["domain", "role", "purpose"]
    DISCOVERY_REQUIRED = ["data_type", "automation", "context", "human_oversight"]
    
    # All critical facts combined
    ALL_CRITICAL = INTAKE_REQUIRED + DISCOVERY_REQUIRED
    
    @staticmethod
    def calculate_confidence(facts: Dict[str, str]) -> ConfidenceLevel:
        """
        Calculate confidence based on number of key conditions met.
        
        Rules:
        - < 3 key conditions → LOW
        - 3-4 key conditions → MEDIUM
        - 5+ key conditions → HIGH
        """
        critical_count = sum(1 for key in StateMachine.ALL_CRITICAL if key in facts and facts[key])
        
        if critical_count < 3:
            return ConfidenceLevel.LOW
        elif critical_count < 5:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.HIGH
    
    @staticmethod
    def determine_state(facts: Dict[str, str], current_state: InterviewState) -> InterviewState:
        """
        Determine the next state based on collected facts.
        
        Transitions:
        - INIT → INTAKE: Always (after first message)
        - INTAKE → DISCOVERY: When domain, role, purpose are present
        - DISCOVERY → CHECKPOINT: When data_type, automation, context are present
        - CHECKPOINT → ASSESSMENT: When risk rules have run and obligations identified
        - ASSESSMENT: Terminal state (no further transitions)
        """
        # Terminal state
        if current_state == InterviewState.ASSESSMENT:
            return InterviewState.ASSESSMENT
        
        # INIT → INTAKE (after any fact extraction)
        if current_state == InterviewState.INIT:
            return InterviewState.INTAKE
        
        # INTAKE → DISCOVERY (when core facts collected)
        if current_state == InterviewState.INTAKE:
            # A fact exists if it's in the dict AND has a non-empty value (even if "no")
            has_intake = all(key in facts and facts[key] and facts[key].strip() != "" for key in StateMachine.INTAKE_REQUIRED)
            if has_intake:
                return InterviewState.DISCOVERY
            return InterviewState.INTAKE
        
        # DISCOVERY → CHECKPOINT (when discovery facts collected)
        if current_state == InterviewState.DISCOVERY:
            # A fact exists if it's in the dict AND has a non-empty value (even if "no")
            has_discovery = all(key in facts and facts[key] and facts[key].strip() != "" for key in StateMachine.DISCOVERY_REQUIRED)
            if has_discovery:
                return InterviewState.CHECKPOINT
            return InterviewState.DISCOVERY
        
        # CHECKPOINT → ASSESSMENT (after risk rules run)
        if current_state == InterviewState.CHECKPOINT:
            # If we have all critical facts and risk rules have been evaluated, move to assessment
            # A fact exists if it's in the dict AND has a non-empty value (even if "no")
            has_all_critical = all(key in facts and facts[key] and facts[key].strip() != "" for key in StateMachine.ALL_CRITICAL)
            if has_all_critical:
                return InterviewState.ASSESSMENT
            return InterviewState.CHECKPOINT
        
        return current_state
    
    @staticmethod
    def get_missing_facts(facts: Dict[str, str], current_state: InterviewState) -> List[str]:
        """
        Get list of facts that are still missing for the current state.
        Note: A fact set to "no" is still a fact, not missing information.
        """
        if current_state == InterviewState.INIT:
            return StateMachine.INTAKE_REQUIRED.copy()
        
        if current_state == InterviewState.INTAKE:
            # A fact exists if it's in the dict AND has a value (even if "no")
            return [key for key in StateMachine.INTAKE_REQUIRED if key not in facts or not facts[key] or facts[key].strip() == ""]
        
        if current_state == InterviewState.DISCOVERY:
            # A fact exists if it's in the dict AND has a value (even if "no")
            return [key for key in StateMachine.DISCOVERY_REQUIRED if key not in facts or not facts[key] or facts[key].strip() == ""]
        
        if current_state == InterviewState.CHECKPOINT:
            # Check if any critical facts are still missing
            # A fact exists if it's in the dict AND has a value (even if "no")
            return [key for key in StateMachine.ALL_CRITICAL if key not in facts or not facts[key] or facts[key].strip() == ""]
        
        return []  # ASSESSMENT state - no missing facts
    
    @staticmethod
    def should_run_deductions(current_state: InterviewState) -> bool:
        """
        Determine if risk rules should run at this state.
        
        Rules run at:
        - INTAKE (to catch prohibited practices early)
        - DISCOVERY (if we have enough info to make preliminary assessment)
        - CHECKPOINT (always)
        - ASSESSMENT (always, for final confirmation)
        """
        return current_state in [
            InterviewState.INTAKE,    # Run early to catch prohibited practices
            InterviewState.DISCOVERY,  # Run preliminary deductions during discovery
            InterviewState.CHECKPOINT,
            InterviewState.ASSESSMENT
        ]
    
    @staticmethod
    def get_state_description(state: InterviewState) -> str:
        """Human-readable description of each state."""
        descriptions = {
            InterviewState.INIT: "Initializing assessment",
            InterviewState.INTAKE: "Gathering core information",
            InterviewState.DISCOVERY: "Exploring system details",
            InterviewState.CHECKPOINT: "Evaluating compliance requirements",
            InterviewState.ASSESSMENT: "Assessment complete — ready for compliance report"
        }
        return descriptions.get(state, "Unknown state")
    
    @staticmethod
    def get_confidence_message(confidence: ConfidenceLevel, risk_level: str) -> str:
        """
        Generate a confidence message to include in bot responses.
        """
        if confidence == ConfidenceLevel.LOW:
            return "Current confidence: LOW — classification may change significantly with additional information."
        elif confidence == ConfidenceLevel.MEDIUM:
            return "Current confidence: MEDIUM — classification may change with additional information."
        else:
            if risk_level in ["HIGH", "UNACCEPTABLE"]:
                return "Current confidence: HIGH — this classification is based on sufficient information."
            else:
                return "Current confidence: HIGH — assessment is complete."

