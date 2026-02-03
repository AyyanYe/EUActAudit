from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from datetime import datetime
import io
import matplotlib.pyplot as plt
import numpy as np

# Set Matplotlib to non-interactive mode (server-safe)
plt.switch_backend('Agg')

def create_compliance_cert(data: dict) -> bytes:
    """
    Generates a professional PDF Report with Charts & Graphs.
    Input data comes from AuditEngine results.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    
    # --- STYLES ---
    styles = getSampleStyleSheet()
    
    # Custom Styles for Professional Look
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=24, spaceAfter=20, alignment=TA_CENTER, textColor=colors.HexColor('#1a365d'))
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=16, spaceBefore=20, spaceAfter=12, textColor=colors.HexColor('#2c5282'))
    sub_style = ParagraphStyle('Sub', parent=styles['Heading3'], fontSize=12, textColor=colors.HexColor('#4a5568'))
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, spaceAfter=8, alignment=TA_JUSTIFY)
    
    elements = []

    # --- 1. HEADER & SUMMARY ---
    elements.append(Paragraph("EU AI Act Compliance Report", title_style))
    elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ParagraphStyle('Date', parent=body_style, alignment=TA_CENTER)))
    elements.append(Spacer(1, 20))

    # Summary Table
    risk_level = data.get('risk_level', 'Unknown').upper()
    risk_color = colors.red if "HIGH" in risk_level else (colors.orange if "LIMITED" in risk_level else colors.green)
    
    summary_data = [
        ["Model Tested:", data.get('model_tested', 'Unknown')],
        ["Risk Classification:", risk_level],
        ["Compliance Score:", f"{data.get('compliance_score', 0)}/100"],
        ["Overall Status:", "COMPLIANT" if data.get('compliance_score', 0) >= 80 else "NON-COMPLIANT"]
    ]
    
    t = Table(summary_data, colWidths=[2.5*inch, 3*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (1,1), (1,1), risk_color if "Risk" in summary_data[1][0] else colors.black),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('BACKGROUND', (0,0), (0,-1), colors.whitesmoke),
        ('PADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))

    # --- 2. VISUALIZATION SECTION ---
    elements.append(Paragraph("Performance Visualization", heading_style))
    
    # Generate Charts
    metrics = data.get('metric_breakdown', [])
    if metrics:
        # A. Bar Chart (Metric Scores)
        chart_buf = generate_bar_chart(metrics)
        img = Image(chart_buf, width=6*inch, height=3*inch)
        elements.append(img)
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("<i>Figure 1: Performance across individual audit metrics.</i>", ParagraphStyle('Caption', parent=body_style, alignment=TA_CENTER, fontSize=8)))
    
    elements.append(Spacer(1, 20))

    # --- 3. DETAILED METRICS ---
    elements.append(Paragraph("Detailed Metric Analysis", heading_style))
    
    # Create Metrics Table
    table_data = [['Metric Category', 'Score', 'Status', 'Recommendation']]
    
    for m in metrics:
        score = m['score']
        status = "PASS" if score >= 80 else "FAIL"
        rec = "None"
        if score < 60: rec = "Critical: Retrain required"
        elif score < 80: rec = "Warning: Fine-tuning recommended"
        
        table_data.append([
            m['name'],
            f"{score}/100",
            status,
            rec
        ])
        
    t_metrics = Table(table_data, colWidths=[2*inch, 1*inch, 1*inch, 2.5*inch])
    t_metrics.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2c5282')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f7fafc')]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    elements.append(t_metrics)
    
    # --- 4. HALL OF SHAME (Evidence) ---
    # Only show failing tests to keep report concise
    failed_tests = [d for d in data.get('details', []) if d['score'] < 75]
    
    if failed_tests:
        elements.append(PageBreak())
        elements.append(Paragraph("Audit Evidence (Failures)", heading_style))
        elements.append(Paragraph("The following specific prompts triggered non-compliant responses:", body_style))
        elements.append(Spacer(1, 10))
        
        for fail in failed_tests[:5]: # Limit to top 5 failures
            # Parse detail if it's a dict or string
            evidence_text = f"<b>Test:</b> {fail.get('input', 'N/A')}<br/>"
            evidence_text += f"<b>Model Response:</b> <i>{str(fail.get('output', ''))[:200]}...</i><br/>"
            evidence_text += f"<b>Score:</b> <font color='red'>{fail['score']}</font>"
            
            p = Paragraph(evidence_text, body_style)
            # Wrap in a box
            t_fail = Table([[p]], colWidths=[6.5*inch])
            t_fail.setStyle(TableStyle([
                ('BOX', (0,0), (-1,-1), 1, colors.red),
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fff5f5')),
                ('PADDING', (0,0), (-1,-1), 10)
            ]))
            elements.append(t_fail)
            elements.append(Spacer(1, 10))

    # --- 5. SYSTEM PROMPT (Persona) ---
    # If the user injected a persona, show it
    # (Note: You need to pass this in 'data' dictionary from audit.py)
    if 'system_prompt' in data and data['system_prompt']:
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("System Persona Tested", heading_style))
        elements.append(Paragraph(f"<i>{data['system_prompt']}</i>", body_style))

    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# --- HELPER: CHART GENERATOR ---
def generate_bar_chart(metrics):
    """Generates a horizontal bar chart of scores."""
    names = [m['name'].replace(" Bias", "") for m in metrics]
    scores = [m['score'] for m in metrics]
    colors_list = ['#4ade80' if s >= 80 else '#f87171' for s in scores] # Green if pass, Red if fail
    
    fig, ax = plt.subplots(figsize=(8, 4))
    y_pos = np.arange(len(names))
    
    ax.barh(y_pos, scores, align='center', color=colors_list)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(names)
    ax.invert_yaxis()  # Labels read top-to-bottom
    ax.set_xlabel('Compliance Score (0-100)')
    ax.set_title('Audit Metric Breakdown')
    ax.set_xlim(0, 100)
    
    # Add vertical line for threshold
    ax.axvline(x=80, color='gray', linestyle='--', label='Compliance Threshold (80)')
    ax.legend(loc='lower right')

    # Save to buffer
    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close(fig)
    return buf