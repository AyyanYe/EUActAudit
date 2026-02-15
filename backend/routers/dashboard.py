"""
Dashboard statistics endpoint.

Aggregates data from Projects, Obligations, Facts, and InterviewLogs
to power the frontend dashboard with real compliance metrics.
"""

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from sqlalchemy import func, case, distinct
from typing import Optional
from datetime import datetime, timedelta

from database import get_db, Project, Fact, Obligation, InterviewLog, AuditRun
from core.auth import get_user_id_optional

router = APIRouter()


@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    """
    Return aggregated dashboard statistics for the authenticated user.

    Response shape:
    {
      summary: { total_assessments, active_assessments, completed_assessments,
                 high_risk_count, compliance_rate, total_obligations },
      risk_distribution: [ { name, value } ... ],
      obligation_breakdown: [ { name, met, unmet, pending, gap, review, planned } ... ],
      recent_projects: [ { id, name, risk_level, status, state, updated_at,
                           obligation_count, met_count, progress } ... ],
      top_gaps: [ { code, title, count } ... ],
      activity_timeline: [ { date, messages } ... ],
    }
    """
    user_id = get_user_id_optional(authorization)

    # ── Base query: projects belonging to this user ──────────────────────
    project_q = db.query(Project)
    if user_id:
        project_q = project_q.filter(Project.user_id == user_id)
    else:
        project_q = project_q.filter(
            (Project.user_id == None) | (Project.user_id == "anonymous")  # noqa: E711
        )
    projects = project_q.order_by(Project.updated_at.desc()).all()
    project_ids = [p.id for p in projects]

    if not project_ids:
        return _empty_response()

    # ── 1. Summary stats ────────────────────────────────────────────────
    total = len(projects)
    active = sum(1 for p in projects if p.interview_state not in ("ASSESSMENT", "TERMINATED", None))
    completed = sum(1 for p in projects if p.interview_state == "ASSESSMENT")
    high_risk = sum(1 for p in projects if (p.risk_level or "").upper() in ("HIGH", "UNACCEPTABLE"))

    # Obligation stats across all user projects
    all_obligations = (
        db.query(Obligation)
        .filter(Obligation.project_id.in_(project_ids))
        .all()
    )
    total_obligations = len(all_obligations)
    met_count = sum(1 for o in all_obligations if (o.status or "").upper() == "MET")
    compliance_rate = round(met_count / total_obligations * 100) if total_obligations else 0

    summary = {
        "total_assessments": total,
        "active_assessments": active,
        "completed_assessments": completed,
        "high_risk_count": high_risk,
        "compliance_rate": compliance_rate,
        "total_obligations": total_obligations,
    }

    # ── 2. Risk distribution (for donut / pie chart) ────────────────────
    risk_counts: dict[str, int] = {}
    for p in projects:
        level = (p.risk_level or "Unknown").upper()
        # Normalize
        if level in ("UNACCEPTABLE",):
            label = "Prohibited"
        elif level == "HIGH":
            label = "High"
        elif level == "LIMITED":
            label = "Limited"
        elif level == "MINIMAL":
            label = "Minimal"
        else:
            label = "Pending"
        risk_counts[label] = risk_counts.get(label, 0) + 1

    risk_distribution = [{"name": k, "value": v} for k, v in risk_counts.items()]

    # ── 3. Obligation status breakdown (for stacked bar) ────────────────
    ob_status_map: dict[str, dict] = {}
    for ob in all_obligations:
        code = ob.code or "OTHER"
        title = ob.title or code
        key = code
        if key not in ob_status_map:
            ob_status_map[key] = {
                "code": code,
                "title": title,
                "met": 0,
                "unmet": 0,
                "pending": 0,
                "gap": 0,
                "review": 0,
                "planned": 0,
            }
        status = (ob.status or "PENDING").lower()
        if status == "met":
            ob_status_map[key]["met"] += 1
        elif status == "unmet":
            ob_status_map[key]["unmet"] += 1
        elif status == "gap_detected":
            ob_status_map[key]["gap"] += 1
        elif status == "under_review":
            ob_status_map[key]["review"] += 1
        elif status == "planned_remediation":
            ob_status_map[key]["planned"] += 1
        else:
            ob_status_map[key]["pending"] += 1

    obligation_breakdown = list(ob_status_map.values())

    # ── 4. Recent projects with progress ────────────────────────────────
    recent_projects = []
    for p in projects[:8]:  # Top 8 most recent
        p_obligations = [o for o in all_obligations if o.project_id == p.id]
        p_total = len(p_obligations)
        p_met = sum(1 for o in p_obligations if (o.status or "").upper() == "MET")
        progress = round(p_met / p_total * 100) if p_total else 0

        recent_projects.append({
            "id": p.id,
            "name": p.name or "Untitled",
            "description": (p.description or "")[:80],
            "risk_level": p.risk_level or "Unknown",
            "status": p.status or "Draft",
            "state": p.interview_state or "INIT",
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "obligation_count": p_total,
            "met_count": p_met,
            "progress": progress,
        })

    # ── 5. Top compliance gaps (most common unmet obligations) ──────────
    gap_counts: dict[str, dict] = {}
    for ob in all_obligations:
        status = (ob.status or "PENDING").lower()
        if status in ("unmet", "gap_detected", "under_review", "pending"):
            code = ob.code or "OTHER"
            if code not in gap_counts:
                gap_counts[code] = {"code": code, "title": ob.title or code, "count": 0}
            gap_counts[code]["count"] += 1

    top_gaps = sorted(gap_counts.values(), key=lambda x: x["count"], reverse=True)[:6]

    # ── 6. Activity timeline (messages per day, last 14 days) ───────────
    fourteen_days_ago = datetime.now() - timedelta(days=14)
    logs = (
        db.query(
            func.date(InterviewLog.timestamp).label("day"),
            func.count(InterviewLog.id).label("cnt"),
        )
        .filter(
            InterviewLog.project_id.in_(project_ids),
            InterviewLog.timestamp >= fourteen_days_ago,
        )
        .group_by(func.date(InterviewLog.timestamp))
        .order_by(func.date(InterviewLog.timestamp))
        .all()
    )

    # Fill in missing days with 0
    activity_timeline = []
    day_map = {str(row.day): row.cnt for row in logs}
    for i in range(14):
        d = (fourteen_days_ago + timedelta(days=i)).date()
        activity_timeline.append({
            "date": d.strftime("%b %d"),
            "messages": day_map.get(str(d), 0),
        })

    return {
        "summary": summary,
        "risk_distribution": risk_distribution,
        "obligation_breakdown": obligation_breakdown,
        "recent_projects": recent_projects,
        "top_gaps": top_gaps,
        "activity_timeline": activity_timeline,
    }


def _empty_response():
    return {
        "summary": {
            "total_assessments": 0,
            "active_assessments": 0,
            "completed_assessments": 0,
            "high_risk_count": 0,
            "compliance_rate": 0,
            "total_obligations": 0,
        },
        "risk_distribution": [],
        "obligation_breakdown": [],
        "recent_projects": [],
        "top_gaps": [],
        "activity_timeline": [],
    }
