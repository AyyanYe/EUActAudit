from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from datetime import datetime
import io
import matplotlib.pyplot as plt
import numpy as np

from core.eu_ai_act_context import get_article_context_for_topic

# Set Matplotlib to non-interactive mode (server-safe)
plt.switch_backend('Agg')

# --- Mapping from obligation codes to topic keys (for RAG lookup) ---
OB_CODE_TO_TOPIC = {
    "ART_14_OVERSIGHT": "human_oversight",
    "ART_10": "data_governance",
    "ART_15": "accuracy_robustness",
    "ART_12": "record_keeping",
    "ART_50": "transparency",
}

# --- Recommendations per topic when status is not MET ---
RECOMMENDATIONS = {
    "human_oversight": (
        "1. Implement a formal human-in-the-loop review process for all consequential AI decisions.\n"
        "2. Designate trained personnel who can override or halt AI decisions at any time.\n"
        "3. Document escalation procedures and ensure a 'stop' mechanism is available per Article 14(4)."
    ),
    "data_governance": (
        "1. Establish bias testing procedures for training data and run them on a regular schedule.\n"
        "2. Ensure datasets are representative of affected demographics and free of systematic errors.\n"
        "3. Document data collection, preparation, and labelling processes per Article 10(2)."
    ),
    "accuracy_robustness": (
        "1. Implement error rate monitoring and establish accuracy benchmarks for your intended purpose.\n"
        "2. Deploy adversarial testing to identify vulnerabilities (data poisoning, model evasion).\n"
        "3. Ensure cybersecurity measures protect the system from unauthorised manipulation per Article 15."
    ),
    "record_keeping": (
        "1. Enable automatic logging of all system operations, inputs, and decisions.\n"
        "2. Ensure logs are retained for at least 6 months (or longer if required by national law).\n"
        "3. Make logs available for post-market monitoring and regulatory inspection per Article 12."
    ),
    "transparency": (
        "1. Ensure a clear, visible notice informs users they are interacting with an AI system.\n"
        "2. For content-generating AI, implement watermarking or machine-readable markers.\n"
        "3. Document your transparency measures and keep them up to date per Article 50."
    ),
}

# --- Priority and timeline per topic ---
TOPIC_PRIORITY = {
    "human_oversight": ("CRITICAL", "Immediate (0-30 days)"),
    "data_governance": ("HIGH", "Short-term (30-90 days)"),
    "accuracy_robustness": ("HIGH", "Short-term (30-90 days)"),
    "record_keeping": ("HIGH", "Short-term (30-90 days)"),
    "transparency": ("MEDIUM", "Medium-term (90-180 days)"),
}

# --- Annex III domain mapping for risk justification ---
ANNEX_III_DOMAINS = {
    "recruitment": "Annex III, Point 4 – Employment, workers management and access to self-employment",
    "hr": "Annex III, Point 4 – Employment, workers management and access to self-employment",
    "education": "Annex III, Point 3 – Education and vocational training",
    "credit_scoring": "Annex III, Point 5(b) – Creditworthiness evaluation",
    "insurance": "Annex III, Point 5(c) – Risk assessment for life and health insurance",
    "healthcare": "Annex III, Point 5(a) – Essential public assistance and healthcare services",
    "law_enforcement": "Annex III, Point 6 – Law enforcement",
    "biometrics": "Annex III, Point 1 – Biometric identification and categorisation",
    "critical_infrastructure": "Annex III, Point 2 – Critical infrastructure management",
    "migration": "Annex III, Point 7 – Migration, asylum and border control",
    "justice": "Annex III, Point 8 – Administration of justice and democratic processes",
}

PROHIBITED_PURPOSES = {
    "social_scoring": "Article 5(1)(c) – Social scoring of natural persons",
    "emotion_recognition": "Article 5(1)(f) – Emotion recognition in workplace/education",
    "subliminal_manipulation": "Article 5(1)(a) – Subliminal manipulation techniques",
}


def _safe_text(text: str) -> str:
    """Escape XML special characters for ReportLab Paragraphs."""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _status_label(status: str) -> str:
    """Convert internal status to human-readable label."""
    s = (status or "PENDING").strip().lower()
    mapping = {
        "met": "MET",
        "planned_remediation": "PLANNED REMEDIATION",
        "planned": "PLANNED REMEDIATION",
        "gap_detected": "GAP DETECTED",
        "under_review": "UNDER REVIEW",
        "pending": "PENDING",
    }
    return mapping.get(s, status.upper())


def _status_color(status: str):
    """Return a ReportLab color for the given status."""
    s = (status or "").strip().lower()
    if s in ("met",):
        return colors.HexColor("#276749")  # green
    if s in ("planned_remediation", "planned"):
        return colors.HexColor("#975a16")  # amber
    if s in ("gap_detected",):
        return colors.HexColor("#9b2c2c")  # red
    return colors.HexColor("#4a5568")  # gray


def _status_bg(status: str):
    """Return a background color for status rows."""
    s = (status or "").strip().lower()
    if s in ("met",):
        return colors.HexColor("#f0fff4")
    if s in ("planned_remediation", "planned"):
        return colors.HexColor("#fffff0")
    if s in ("gap_detected",):
        return colors.HexColor("#fff5f5")
    return colors.HexColor("#f7fafc")


def create_compliance_cert(data: dict) -> bytes:
    """
    Generates a comprehensive EU AI Act Compliance Assessment Report.
    
    Expected keys in data:
        model_tested, description, risk_level, compliance_score,
        compliance_status, interview_state, metric_breakdown,
        obligations (list of dicts with code/title/description/status),
        facts (dict of key-value pairs)
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=60,
        leftMargin=60,
        topMargin=60,
        bottomMargin=60,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Heading1"],
        fontSize=26, spaceAfter=6, alignment=TA_CENTER,
        textColor=colors.HexColor("#1a365d"),
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle", parent=styles["Heading2"],
        fontSize=14, spaceAfter=4, alignment=TA_CENTER,
        textColor=colors.HexColor("#4a5568"),
    )
    heading_style = ParagraphStyle(
        "SectionHeading", parent=styles["Heading2"],
        fontSize=16, spaceBefore=22, spaceAfter=10,
        textColor=colors.HexColor("#2c5282"),
    )
    sub_heading_style = ParagraphStyle(
        "SubHeading", parent=styles["Heading3"],
        fontSize=12, spaceBefore=14, spaceAfter=6,
        textColor=colors.HexColor("#2d3748"),
    )
    body_style = ParagraphStyle(
        "BodyText", parent=styles["Normal"],
        fontSize=10, spaceAfter=6, alignment=TA_JUSTIFY,
        leading=14,
    )
    small_style = ParagraphStyle(
        "SmallText", parent=styles["Normal"],
        fontSize=8, spaceAfter=4, alignment=TA_CENTER,
        textColor=colors.HexColor("#718096"),
    )
    bold_body = ParagraphStyle(
        "BoldBody", parent=body_style, fontName="Helvetica-Bold",
    )

    elements = []

    # =====================================================================
    # SECTION 1: COVER PAGE
    # =====================================================================
    elements.append(Spacer(1, 80))
    elements.append(Paragraph("EU AI Act", title_style))
    elements.append(Paragraph("Compliance Assessment Report", title_style))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        _safe_text(data.get("model_tested", "Unnamed System")),
        subtitle_style,
    ))
    if data.get("description"):
        elements.append(Paragraph(
            f"<i>{_safe_text(data['description'])}</i>",
            ParagraphStyle("Desc", parent=body_style, alignment=TA_CENTER),
        ))
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(
        f"Generated on {datetime.now().strftime('%d %B %Y at %H:%M')}",
        small_style,
    ))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        "<i>DISCLAIMER: This report is a preliminary analysis generated by an automated tool. "
        "It is for informational purposes only and does not constitute legal advice. "
        "Consult a qualified legal professional before making compliance decisions.</i>",
        ParagraphStyle("Disclaimer", parent=small_style, alignment=TA_JUSTIFY, fontSize=8),
    ))
    elements.append(PageBreak())

    # =====================================================================
    # SECTION 2: EXECUTIVE SUMMARY
    # =====================================================================
    elements.append(Paragraph("1. Executive Summary", heading_style))

    risk_level = data.get("risk_level", "Unknown").upper()
    compliance_score = data.get("compliance_score", 0)

    # Calculate compliance score from obligations if not already calculated
    obligations_list = data.get("obligations", [])
    if obligations_list:
        total_ob = len(obligations_list)
        met_ob = sum(
            1 for ob in obligations_list
            if (ob.get("status") or "").strip().lower() in ("met", "planned_remediation", "planned")
        )
        compliance_score = int((met_ob / total_ob) * 100) if total_ob > 0 else 0

    if compliance_score >= 80:
        verdict = "Likely Compliant (pending implementation of planned measures)"
    elif compliance_score >= 50:
        verdict = "Gaps Identified - Remediation Required"
    else:
        verdict = "Significant Non-Compliance Detected"

    risk_color = colors.HexColor("#9b2c2c")  # red default
    if "LIMITED" in risk_level:
        risk_color = colors.HexColor("#975a16")
    elif "MINIMAL" in risk_level:
        risk_color = colors.HexColor("#276749")
    elif "UNKNOWN" in risk_level:
        risk_color = colors.HexColor("#4a5568")

    summary_rows = [
        ["System Name", _safe_text(data.get("model_tested", "Unknown"))],
        ["Risk Classification", risk_level],
        ["Compliance Score", f"{compliance_score}%"],
        ["Overall Verdict", verdict],
        ["Assessment State", data.get("interview_state", "Unknown")],
    ]

    t = Table(summary_rows, colWidths=[2.2 * inch, 4 * inch])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (1, 1), (1, 1), risk_color),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#edf2f7")),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 10))

    # Compliance bar chart
    if obligations_list:
        chart_buf = _generate_obligation_chart(obligations_list)
        if chart_buf:
            from reportlab.platypus import Image
            img = Image(chart_buf, width=5.5 * inch, height=2.5 * inch)
            elements.append(img)
            elements.append(Paragraph(
                "<i>Figure 1: Obligation compliance status breakdown.</i>",
                small_style,
            ))
    elements.append(Spacer(1, 10))

    # =====================================================================
    # SECTION 3: SYSTEM PROFILE
    # =====================================================================
    elements.append(Paragraph("2. System Profile", heading_style))
    elements.append(Paragraph(
        "The following information was collected during the compliance interview:",
        body_style,
    ))

    facts = data.get("facts", {})
    profile_fields = [
        ("domain", "Industry / Domain"),
        ("role", "Provider or Deployer"),
        ("purpose", "System Purpose"),
        ("data_type", "Data Processed"),
        ("automation", "Automation Level"),
        ("context", "Deployment Context"),
        ("capability", "System Capability"),
        ("special_category_data", "Special Category Data"),
    ]

    profile_rows = [["Field", "Value"]]
    for key, label in profile_fields:
        val = facts.get(key)
        if val:
            display_val = _safe_text(str(val).replace("_", " ").title())
            profile_rows.append([label, display_val])

    if len(profile_rows) > 1:
        t_profile = Table(profile_rows, colWidths=[2.5 * inch, 3.7 * inch])
        t_profile.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5282")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(t_profile)
    else:
        elements.append(Paragraph("<i>No profile facts were collected.</i>", body_style))
    elements.append(Spacer(1, 10))

    # =====================================================================
    # SECTION 4: ARTICLE-BY-ARTICLE COMPLIANCE ANALYSIS
    # =====================================================================
    elements.append(PageBreak())
    elements.append(Paragraph("3. Article-by-Article Compliance Analysis", heading_style))

    if not obligations_list:
        elements.append(Paragraph(
            "<i>No specific obligations were triggered during the assessment.</i>",
            body_style,
        ))
    else:
        for ob in obligations_list:
            code = ob.get("code", "Unknown")
            title = ob.get("title", code)
            status = ob.get("status", "PENDING")
            status_lbl = _status_label(status)
            topic_key = OB_CODE_TO_TOPIC.get(code)

            # Sub-heading: Article code and title
            elements.append(Paragraph(
                f"{_safe_text(code)} &ndash; {_safe_text(title)}",
                sub_heading_style,
            ))

            # Status badge
            status_text = f'<font color="{_status_color(status).hexval()}">'
            status_text += f'<b>Status: {status_lbl}</b></font>'
            elements.append(Paragraph(status_text, body_style))

            # What the law requires (from RAG)
            if topic_key:
                rag_text = get_article_context_for_topic(topic_key)
                if rag_text:
                    # Truncate to first 500 chars for PDF readability
                    truncated = rag_text[:500]
                    if len(rag_text) > 500:
                        truncated += "..."
                    elements.append(Paragraph("<b>What the law requires:</b>", bold_body))
                    elements.append(Paragraph(
                        f"<i>{_safe_text(truncated)}</i>",
                        ParagraphStyle("LawText", parent=body_style, fontSize=9,
                                       textColor=colors.HexColor("#4a5568"),
                                       leftIndent=12),
                    ))

            # Current status explanation
            if topic_key:
                fact_val = facts.get(topic_key, "")
                if fact_val:
                    readable = str(fact_val).replace("_", " ").title()
                    elements.append(Paragraph("<b>Your current status:</b>", bold_body))
                    elements.append(Paragraph(
                        f'You indicated that {topic_key.replace("_", " ")} is: '
                        f'<b>{_safe_text(readable)}</b>.',
                        body_style,
                    ))

            # Recommendation (if not MET)
            s_lower = (status or "").strip().lower()
            if s_lower not in ("met",) and topic_key and topic_key in RECOMMENDATIONS:
                elements.append(Paragraph("<b>Recommended actions:</b>", bold_body))
                for line in RECOMMENDATIONS[topic_key].split("\n"):
                    line = line.strip()
                    if line:
                        elements.append(Paragraph(
                            _safe_text(line),
                            ParagraphStyle("RecLine", parent=body_style, leftIndent=18, fontSize=9),
                        ))

            elements.append(Spacer(1, 10))

    # =====================================================================
    # SECTION 5: REMEDIATION ROADMAP
    # =====================================================================
    gaps = [
        ob for ob in obligations_list
        if (ob.get("status") or "").strip().lower() not in ("met",)
    ]
    if gaps:
        elements.append(PageBreak())
        elements.append(Paragraph("4. Remediation Roadmap", heading_style))
        elements.append(Paragraph(
            "The following action items are required to bring the system into compliance:",
            body_style,
        ))
        elements.append(Spacer(1, 8))

        roadmap_rows = [["#", "Obligation", "Priority", "Timeline", "Key Actions"]]
        for idx, ob in enumerate(gaps, 1):
            code = ob.get("code", "Unknown")
            title = ob.get("title", code)
            topic_key = OB_CODE_TO_TOPIC.get(code, "")
            priority, timeline = TOPIC_PRIORITY.get(topic_key, ("MEDIUM", "Medium-term"))
            rec = RECOMMENDATIONS.get(topic_key, "Consult a legal professional.")
            # Shorten rec for table
            short_rec = rec.split("\n")[0].strip() if rec else ""
            if short_rec.startswith("1. "):
                short_rec = short_rec[3:]
            roadmap_rows.append([
                str(idx),
                _safe_text(f"{code}\n{title}"),
                priority,
                timeline,
                _safe_text(short_rec[:80]),
            ])

        t_roadmap = Table(
            roadmap_rows,
            colWidths=[0.3 * inch, 1.4 * inch, 0.8 * inch, 1.2 * inch, 2.5 * inch],
        )
        t_roadmap.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5282")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(t_roadmap)
        elements.append(Spacer(1, 10))

    # =====================================================================
    # SECTION 6: RISK CLASSIFICATION JUSTIFICATION
    # =====================================================================
    elements.append(Paragraph("5. Risk Classification Justification", heading_style))

    domain = facts.get("domain", "").lower()
    purpose = facts.get("purpose", "").lower()

    if "UNACCEPTABLE" in risk_level:
        prohibition = "Unknown prohibited practice"
        for key, desc in PROHIBITED_PURPOSES.items():
            if key in purpose:
                prohibition = desc
                break
        elements.append(Paragraph(
            f"This system has been classified as <b>UNACCEPTABLE</b> (Prohibited) because it falls "
            f"under <b>{_safe_text(prohibition)}</b> of the EU AI Act. "
            f"Systems classified as prohibited cannot be legally placed on the EU market under any circumstances. "
            f"Fines for infringement can reach up to EUR 35,000,000 or 7% of global annual turnover.",
            body_style,
        ))
    elif "HIGH" in risk_level:
        annex_category = "a high-risk category under Annex III"
        for key, desc in ANNEX_III_DOMAINS.items():
            if key in domain or key in purpose:
                annex_category = desc
                break
        elements.append(Paragraph(
            f"This system has been classified as <b>HIGH RISK</b> because it falls under "
            f"<b>{_safe_text(annex_category)}</b> of the EU AI Act. "
            f"High-risk AI systems must comply with the requirements in Articles 8-15 (risk management, "
            f"data governance, transparency, human oversight, accuracy, and record-keeping). "
            f"Non-compliance can result in fines of up to EUR 15,000,000 or 3% of global annual turnover.",
            body_style,
        ))
    elif "LIMITED" in risk_level:
        elements.append(Paragraph(
            "This system has been classified as <b>LIMITED RISK</b>. Under Article 50 of the EU AI Act, "
            "AI systems that interact directly with natural persons must transparently disclose that users "
            "are interacting with an AI. For content-generating systems, outputs must be marked as AI-generated. "
            "Limited risk systems do not require the full compliance regime of high-risk systems.",
            body_style,
        ))
    else:
        elements.append(Paragraph(
            "This system has been classified as <b>MINIMAL RISK</b>. Under the EU AI Act, minimal risk "
            "AI systems can be freely used in the EU without specific compliance obligations beyond "
            "voluntary codes of conduct. No mandatory requirements apply.",
            body_style,
        ))
    elements.append(Spacer(1, 10))

    # =====================================================================
    # SECTION 7: APPENDIX - FULL FACT REGISTRY
    # =====================================================================
    elements.append(PageBreak())
    elements.append(Paragraph("Appendix: Full Fact Registry", heading_style))
    elements.append(Paragraph(
        "All information collected during the compliance interview:",
        body_style,
    ))

    skip_keys = {"workflow_steps", "confidence_scores"}
    fact_rows = [["Fact", "Value"]]
    for key, val in facts.items():
        if key in skip_keys:
            continue
        display_key = key.replace("_", " ").title()
        display_val = str(val).replace("_", " ").title() if val else "Not provided"
        fact_rows.append([_safe_text(display_key), _safe_text(display_val[:120])])

    if len(fact_rows) > 1:
        t_facts = Table(fact_rows, colWidths=[2.5 * inch, 3.7 * inch])
        t_facts.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5282")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(t_facts)
    else:
        elements.append(Paragraph("<i>No facts were collected.</i>", body_style))

    # Footer
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(
        "--- End of Report ---",
        ParagraphStyle("Footer", parent=small_style, alignment=TA_CENTER),
    ))
    elements.append(Paragraph(
        "Generated by AuditGenius | EU AI Act Compliance Platform",
        small_style,
    ))

    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


# --- HELPER: Obligation status chart ---
def _generate_obligation_chart(obligations: list) -> io.BytesIO | None:
    """Generate a horizontal bar chart showing obligation compliance status."""
    if not obligations:
        return None

    names = []
    score_values = []
    bar_colors = []

    for ob in obligations:
        code = ob.get("code", "Unknown")
        status = (ob.get("status") or "PENDING").strip().lower()

        names.append(code.replace("ART_", "Art ").replace("_", " "))

        if status in ("met",):
            score_values.append(100)
            bar_colors.append("#48bb78")  # green
        elif status in ("planned_remediation", "planned"):
            score_values.append(70)
            bar_colors.append("#ecc94b")  # yellow
        elif status in ("under_review",):
            score_values.append(50)
            bar_colors.append("#ed8936")  # orange
        elif status in ("gap_detected",):
            score_values.append(20)
            bar_colors.append("#fc8181")  # red
        else:
            score_values.append(10)
            bar_colors.append("#a0aec0")  # gray

    fig, ax = plt.subplots(figsize=(7, max(2, len(names) * 0.6)))
    y_pos = np.arange(len(names))

    ax.barh(y_pos, score_values, align="center", color=bar_colors, height=0.5)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Compliance Level", fontsize=9)
    ax.set_title("Obligation Status Overview", fontsize=11, fontweight="bold")
    ax.set_xlim(0, 110)

    # Add status labels on bars
    for i, (val, status_name) in enumerate(zip(score_values, [_status_label(ob.get("status", "")) for ob in obligations])):
        ax.text(val + 2, i, status_name, va="center", fontsize=7)

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", dpi=120)
    buf.seek(0)
    plt.close(fig)
    return buf
