"""PDF export using ReportLab from the audit decision + agent outputs."""
import io
from datetime import datetime, timezone
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)


VERDICT_COLOR_HEX = {
    "CLEAR": "#00875A",
    "MINOR_FOLLOWUP": "#FFB000",
    "ELEVATED_REVIEW": "#FF8800",
    "CRITICAL_ESCALATE": "#D00000",
}

KLEIN_BLUE = colors.HexColor("#002FA7")
SLATE = colors.HexColor("#6B7280")
SLATE_HEX = "#6B7280"
BORDER = colors.HexColor("#E5E7EB")


def build_pdf(audit: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
        topMargin=0.7 * inch, bottomMargin=0.7 * inch,
        title=f"SentinelAI Audit — {audit.get('title','Untitled')}",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Title"], fontSize=22, textColor=colors.HexColor("#0A0A0A"), spaceAfter=4)
    sub_style = ParagraphStyle("sub", parent=styles["Normal"], fontSize=9, textColor=SLATE, leading=12, spaceAfter=12)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=13, textColor=KLEIN_BLUE,
                        spaceBefore=14, spaceAfter=6, leading=15)
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=10, leading=14, textColor=colors.HexColor("#0A0A0A"))
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, textColor=SLATE, leading=10)

    story = []
    decision = audit.get("decision") or {}
    verdict = decision.get("verdict", "—")
    v_color_hex = VERDICT_COLOR_HEX.get(verdict, SLATE_HEX)

    story.append(Paragraph("SentinelAI Executive Audit Report", title_style))
    story.append(Paragraph(
        f"{audit.get('title','Untitled')} &nbsp;·&nbsp; Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        sub_style,
    ))

    # KPI table
    kpi_data = [[
        Paragraph("<b>VERDICT</b>", small),
        Paragraph("<b>OVERALL RISK</b>", small),
        Paragraph("<b>CONFIDENCE</b>", small),
        Paragraph("<b>AGENTS</b>", small),
    ], [
        Paragraph(f'<font color="{v_color_hex}"><b>{verdict}</b></font>', body),
        Paragraph(f"<b>{decision.get('overall_risk_score',0)}/100</b>", body),
        Paragraph(f"<b>{int((decision.get('confidence') or 0)*100)}%</b>", body),
        Paragraph(f"<b>{len(audit.get('agents',[]))}</b>", body),
    ]]
    kpi = Table(kpi_data, colWidths=[1.7 * inch] * 4)
    kpi.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F7F7F9")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(kpi)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Executive Summary", h2))
    story.append(Paragraph(decision.get("executive_summary", "—"), body))

    story.append(Paragraph("Key Findings", h2))
    for k in (decision.get("key_findings") or []):
        story.append(Paragraph(f"• {k}", body))
    if not decision.get("key_findings"):
        story.append(Paragraph("No key findings reported.", body))

    story.append(Paragraph("Recommendations", h2))
    for r in (decision.get("recommendations") or []):
        story.append(Paragraph(f"• {r}", body))

    # Agent scores table
    story.append(Paragraph("Agent Risk Scores", h2))
    agents = audit.get("agents", [])
    rows = [[Paragraph("<b>AGENT</b>", small), Paragraph("<b>STATUS</b>", small), Paragraph("<b>RISK</b>", small), Paragraph("<b>SUMMARY</b>", small)]]
    for a in agents:
        out = a.get("output") or {}
        rows.append([
            Paragraph(a.get("agent", "—"), body),
            Paragraph(a.get("status", "—"), body),
            Paragraph(str(out.get("risk_score", "—")), body),
            Paragraph(out.get("summary", "—")[:160], body),
        ])
    agent_tbl = Table(rows, colWidths=[1.3 * inch, 0.8 * inch, 0.6 * inch, 4.0 * inch])
    agent_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F7F7F9")),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(agent_tbl)

    # Detailed findings
    story.append(PageBreak())
    story.append(Paragraph("Detailed Findings", h2))

    finding_rows = [[Paragraph("<b>AGENT</b>", small), Paragraph("<b>TYPE</b>", small),
                     Paragraph("<b>SEVERITY</b>", small), Paragraph("<b>DESCRIPTION</b>", small)]]
    for a in agents:
        out = a.get("output") or {}
        for f in (out.get("findings") or []):
            sev = (f.get("severity") or "—").upper()
            sev_hex = "#D00000" if sev == "HIGH" else "#FFB000" if sev == "MEDIUM" else SLATE_HEX
            finding_rows.append([
                Paragraph(a.get("agent", "—"), body),
                Paragraph(str(f.get("type") or f.get("rule") or "—"), body),
                Paragraph(f'<font color="{sev_hex}">{sev}</font>', body),
                Paragraph(str(f.get("description", "—"))[:300], body),
            ])
    if len(finding_rows) == 1:
        finding_rows.append([Paragraph("—", body)] * 4)
    findings_tbl = Table(finding_rows, colWidths=[1.2 * inch, 1.4 * inch, 0.8 * inch, 3.3 * inch], repeatRows=1)
    findings_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F7F7F9")),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(findings_tbl)

    story.append(Spacer(1, 18))
    story.append(Paragraph("Rationale", h2))
    story.append(Paragraph(decision.get("rationale", "—"), body))

    story.append(Spacer(1, 24))
    story.append(Paragraph(
        "Generated by SentinelAI Multi-Agent Audit Framework · Powered by Google Gemini · Confidential",
        small,
    ))

    doc.build(story)
    return buf.getvalue()
