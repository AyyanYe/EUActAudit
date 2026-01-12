from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO

def create_compliance_cert(data):
    """
    Generates a professional PDF Compliance Certificate.
    Data expected: {'compliance_score': 85.0, 'status': 'COMPLIANT', ...}
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # 1. Title
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=24, spaceAfter=20)
    story.append(Paragraph("EU AI Act Compliance Certificate", title_style))
    story.append(Spacer(1, 12))

    # 2. Executive Summary
    summary_text = f"""
    <b>Date:</b> {data.get('timestamp', 'N/A')}<br/>
    <b>Model Tested:</b> {data.get('model_name', 'Unknown')}<br/>
    <b>Overall Score:</b> {data.get('compliance_score', 0)}/100
    """
    story.append(Paragraph(summary_text, styles['Normal']))
    story.append(Spacer(1, 20))

    # 3. Status Badge
    status = data.get('status', 'UNKNOWN')
    color = "green" if status == "COMPLIANT" else "red"
    status_text = f"<font color='{color}' size='18'><b>STATUS: {status}</b></font>"
    story.append(Paragraph(status_text, styles['Normal']))
    story.append(Spacer(1, 20))

    # 4. Detailed Scores Table
    # (Mock data structure based on your PDF)
    table_data = [
        ['Metric Category', 'Score', 'Result'],
        ['Gender Fairness', '92/100', 'PASS'],
        ['Data Transparency', '85/100', 'PASS'],
        ['Robustness', '78/100', 'WARN']
    ]
    
    t = Table(table_data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(t)
    
    # 5. Build
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()