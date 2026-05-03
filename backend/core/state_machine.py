# backend/core/state_machine.py
"""
Deterministic State Machine for Governance Interview Process.

States: INIT → INTAKE → DISCOVERY → WORKFLOW → CHECKPOINT → ASSESSMENT

Each state has:
- Entry conditions
- Required facts to collect
- Exit conditions (what moves to next state)
- What deductions run at this state
"""

import json
from typing import Dict, List, Tuple, Optional
from enum import Enum


class InterviewState(str, Enum):
    """The six states of the interview process."""

    INIT = "INIT"  # Project created, no facts yet
    INTAKE = "INTAKE"  # Gathering core facts (domain, role, purpose)
    DISCOVERY = "DISCOVERY"  # Deep dive (data types, automation, context)
    WORKFLOW = "WORKFLOW"  # Gathering operational workflow steps (NEW)
    CHECKPOINT = "CHECKPOINT"  # Running risk rules, checking completeness
    ASSESSMENT = "ASSESSMENT"  # Final state, obligations identified


class ConfidenceLevel(str, Enum):
    """Confidence in the current classification."""

    LOW = "LOW"  # < 3 key conditions met
    MEDIUM = "MEDIUM"  # 3-4 key conditions met
    HIGH = "HIGH"  # 5+ key conditions met


class StateMachine:
    """
    Manages state transitions and determines what to ask next.
    """

    # Critical facts required for each state
    INTAKE_REQUIRED = ["domain", "role", "purpose"]
    DISCOVERY_REQUIRED = ["data_type", "automation", "context", "human_oversight"]

    # All critical facts combined (intake + discovery)
    ALL_CRITICAL = INTAKE_REQUIRED + DISCOVERY_REQUIRED

    @staticmethod
    def _has_workflow_steps(facts: Dict[str, str]) -> bool:
        """Check if workflow_steps is a non-empty list (may be stored as JSON string)."""
        raw = facts.get("workflow_steps", "")
        if not raw:
            return False
        if isinstance(raw, list):
            return len(raw) >= 2
        # Stored as JSON string in DB
        try:
            parsed = json.loads(raw)
            return isinstance(parsed, list) and len(parsed) >= 2
        except (json.JSONDecodeError, TypeError):
            return False

    @staticmethod
    def calculate_confidence(facts: Dict[str, str]) -> ConfidenceLevel:
        """
        Calculate confidence based on number of key conditions met.

        Rules:
        - < 3 key conditions → LOW
        - 3-4 key conditions → MEDIUM
        - 5+ key conditions → HIGH
        """
        critical_count = sum(
            1 for key in StateMachine.ALL_CRITICAL if key in facts and facts[key]
        )
        # Bonus for having workflow steps
        if StateMachine._has_workflow_steps(facts):
            critical_count += 1

        if critical_count < 3:
            return ConfidenceLevel.LOW
        elif critical_count < 5:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.HIGH

    @staticmethod
    def determine_state(
        facts: Dict[str, str], current_state: InterviewState
    ) -> InterviewState:
        """
        Determine the next state based on collected facts.

        Transitions:
        - INIT → INTAKE: Always (after first message)
        - INTAKE → DISCOVERY: When domain, role, purpose are present
        - DISCOVERY → WORKFLOW: When data_type, automation, context, human_oversight are present
        - WORKFLOW → CHECKPOINT: When workflow_steps has 2+ steps
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
            has_intake = all(
                key in facts and facts[key] and facts[key].strip() != ""
                for key in StateMachine.INTAKE_REQUIRED
            )
            if has_intake:
                return InterviewState.DISCOVERY
            return InterviewState.INTAKE

        # DISCOVERY → WORKFLOW (when discovery facts collected)
        if current_state == InterviewState.DISCOVERY:
            has_discovery = all(
                key in facts and facts[key] and facts[key].strip() != ""
                for key in StateMachine.DISCOVERY_REQUIRED
            )
            if has_discovery:
                return InterviewState.WORKFLOW
            return InterviewState.DISCOVERY

        # WORKFLOW → CHECKPOINT (when workflow steps are captured)
        if current_state == InterviewState.WORKFLOW:
            if StateMachine._has_workflow_steps(facts):
                return InterviewState.CHECKPOINT
            return InterviewState.WORKFLOW

        # CHECKPOINT → ASSESSMENT (after risk rules run)
        if current_state == InterviewState.CHECKPOINT:
            has_all_critical = all(
                key in facts and facts[key] and facts[key].strip() != ""
                for key in StateMachine.ALL_CRITICAL
            )
            if has_all_critical:
                return InterviewState.ASSESSMENT
            return InterviewState.CHECKPOINT

        return current_state

    @staticmethod
    def get_missing_facts(
        facts: Dict[str, str], current_state: InterviewState
    ) -> List[str]:
        """
        Get list of facts that are still missing for the current state.
        Note: A fact set to "no" is still a fact, not missing information.
        """
        if current_state == InterviewState.INIT:
            return StateMachine.INTAKE_REQUIRED.copy()

        if current_state == InterviewState.INTAKE:
            return [
                key
                for key in StateMachine.INTAKE_REQUIRED
                if key not in facts or not facts[key] or facts[key].strip() == ""
            ]

        if current_state == InterviewState.DISCOVERY:
            return [
                key
                for key in StateMachine.DISCOVERY_REQUIRED
                if key not in facts or not facts[key] or facts[key].strip() == ""
            ]

        if current_state == InterviewState.WORKFLOW:
            # Workflow state: the "missing fact" is workflow_steps
            if not StateMachine._has_workflow_steps(facts):
                return ["workflow_steps"]
            return []

        if current_state == InterviewState.CHECKPOINT:
            return [
                key
                for key in StateMachine.ALL_CRITICAL
                if key not in facts or not facts[key] or facts[key].strip() == ""
            ]

        return []  # ASSESSMENT state - no missing facts

    @staticmethod
    def should_run_deductions(current_state: InterviewState) -> bool:
        """
        Determine if risk rules should run at this state.

        Prohibited practice detection runs early (INTAKE/DISCOVERY).
        Full compliance evaluation (obligations) only at CHECKPOINT+.
        WORKFLOW state does NOT run deductions -- we're still gathering info.
        """
        return current_state in [
            InterviewState.INTAKE,  # Only for prohibited practice detection
            InterviewState.DISCOVERY,  # Only for prohibited practice detection
            InterviewState.CHECKPOINT,  # Full compliance evaluation
            InterviewState.ASSESSMENT,  # Full compliance evaluation
        ]

    @staticmethod
    def is_full_evaluation_state(current_state: InterviewState) -> bool:
        """Returns True if the state allows full obligation creation (not just prohibited detection)."""
        return current_state in [
            InterviewState.CHECKPOINT,
            InterviewState.ASSESSMENT,
        ]

    @staticmethod
    def get_state_description(state: InterviewState) -> str:
        """Human-readable description of each state."""
        descriptions = {
            InterviewState.INIT: "Initializing assessment",
            InterviewState.INTAKE: "Gathering core information",
            InterviewState.DISCOVERY: "Exploring system details",
            InterviewState.WORKFLOW: "Understanding operational workflow",
            InterviewState.CHECKPOINT: "Evaluating compliance requirements",
            InterviewState.ASSESSMENT: "Assessment complete — ready for compliance report",
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
