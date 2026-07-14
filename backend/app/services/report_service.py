"""Renders a PDF risk-analysis report from already-computed analysis data.

Pure formatting -- no analysis logic lives here (see app/models/report.py
docstring for why). Colors mirror the same tokens the frontend uses
(frontend/src/index.css @theme, frontend/src/components/DependencyGraph.tsx
COLORS) so the report reads as the same document, not a generic export.
Times-Roman / Helvetica / Courier stand in for the web app's
Newsreader / Public Sans / IBM Plex Mono (serif / sans / mono) without
needing to embed custom font files into the PDF.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.report import ReportRequest

INK = colors.HexColor("#151a2d")
SLATE_BODY = colors.HexColor("#4a5268")
LEDGER = colors.HexColor("#dce0e8")
LEDGER_SOFT = colors.HexColor("#edeff3")
REDLINE = colors.HexColor("#9c2b37")
SEAL_AMBER = colors.HexColor("#b07c25")

_SEVERITY_COLOR = {"high": REDLINE, "medium": SEAL_AMBER, "low": SLATE_BODY}
_SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}

_styles = getSampleStyleSheet()
_title_style = ParagraphStyle("ReportTitle", parent=_styles["Title"], fontName="Times-Bold", fontSize=18, textColor=INK, spaceAfter=4)
_subtitle_style = ParagraphStyle("ReportSubtitle", parent=_styles["Normal"], fontName="Helvetica", fontSize=11, textColor=SLATE_BODY, spaceAfter=2)
_meta_style = ParagraphStyle("ReportMeta", parent=_styles["Normal"], fontName="Courier", fontSize=8.5, textColor=SLATE_BODY, spaceAfter=16)
_h2_style = ParagraphStyle("ReportH2", parent=_styles["Heading2"], fontName="Times-Bold", fontSize=13, textColor=INK, spaceBefore=16, spaceAfter=8)
_body_style = ParagraphStyle("ReportBody", parent=_styles["Normal"], fontName="Helvetica", fontSize=9, leading=13, textColor=INK)
_cell_style = ParagraphStyle("ReportCell", parent=_body_style, fontSize=8.5, leading=11)
_disclaimer_style = ParagraphStyle("ReportDisclaimer", parent=_styles["Normal"], fontName="Helvetica-Oblique", fontSize=8, textColor=SLATE_BODY, spaceBefore=20)

_TABLE_STYLE = TableStyle(
    [
        ("GRID", (0, 0), (-1, -1), 0.75, LEDGER),
        ("BACKGROUND", (0, 0), (-1, 0), LEDGER_SOFT),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
)


def _escape(text: str) -> str:
    """reportlab's Paragraph uses a small HTML-like markup language, so raw
    '&'/'<'/'>' in clause text or AI-generated explanations would otherwise
    be interpreted as (broken) markup instead of literal characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _p(text: str, style: ParagraphStyle = _cell_style) -> Paragraph:
    return Paragraph(_escape(text), style)


def _p_lines(*lines: str, style: ParagraphStyle = _cell_style) -> Paragraph:
    safe = "<br/>".join(_escape(line) for line in lines if line)
    return Paragraph(safe or "--", style)


def _footer(canvas, _doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(SLATE_BODY)
    canvas.drawString(0.85 * inch, 0.5 * inch, "LexTwin AI -- Contract & SOW Risk Analysis Report")
    canvas.drawRightString(LETTER[0] - 0.85 * inch, 0.5 * inch, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def _risk_summary_section(request: ReportRequest) -> list:
    story: list = [_p("Risk Summary", _h2_style)]
    if not request.risk_flags:
        story.append(_p("No risks flagged for this document pair."))
        return story

    counts = {"high": 0, "medium": 0, "low": 0}
    for flag in request.risk_flags:
        counts[flag.severity] = counts.get(flag.severity, 0) + 1
    story.append(_p(f"{counts['high']} high · {counts['medium']} medium · {counts['low']} low", _body_style))
    story.append(Spacer(1, 6))

    rows: list = [["Severity", "Type", "Finding"]]
    sorted_flags = sorted(request.risk_flags, key=lambda f: _SEVERITY_RANK.get(f.severity, 3))
    for flag in sorted_flags:
        severity_style = ParagraphStyle(
            f"sev-{flag.id}", parent=_cell_style, textColor=_SEVERITY_COLOR.get(flag.severity, INK), fontName="Helvetica-Bold"
        )
        rows.append(
            [
                _p(flag.severity.upper(), severity_style),
                _p(flag.kind.replace("_", " ").title()),
                _p_lines(flag.title, flag.description),
            ]
        )
    table = Table(rows, colWidths=[0.9 * inch, 1.3 * inch, 4.4 * inch], repeatRows=1)
    table.setStyle(_TABLE_STYLE)
    story.append(table)
    return story


def _contradiction_details_section(request: ReportRequest) -> list:
    contradiction_flags = [f for f in request.risk_flags if f.confidence is not None]
    if not contradiction_flags:
        return []

    story: list = [_p("Contradiction Details", _h2_style)]
    rows: list = [["Finding", "Confidence", "Explanation"]]
    for flag in contradiction_flags:
        rows.append([_p(flag.title), _p(f"{round(flag.confidence * 100)}%"), _p(flag.description)])
    table = Table(rows, colWidths=[2.0 * inch, 0.9 * inch, 3.7 * inch], repeatRows=1)
    table.setStyle(_TABLE_STYLE)
    story.append(table)
    return story


def _obligations_section(request: ReportRequest) -> list:
    story: list = [_p("Obligations", _h2_style)]
    if not request.obligations:
        story.append(_p("No obligations detected in these documents."))
        return story

    rows: list = [["Party", "Section", "Deadline", "Obligation"]]
    for obligation in request.obligations:
        deadline = f"{obligation.deadline_days}d" if obligation.deadline_days is not None else "--"
        rows.append(
            [
                _p(obligation.responsible_party or "Unspecified"),
                _p(obligation.section_number or "--"),
                _p(deadline),
                _p(obligation.text),
            ]
        )
    table = Table(rows, colWidths=[1.2 * inch, 0.7 * inch, 0.7 * inch, 3.9 * inch], repeatRows=1)
    table.setStyle(_TABLE_STYLE)
    story.append(table)
    return story


def _audit_trail_section(request: ReportRequest) -> list:
    story: list = [_p("Audit Trail", _h2_style)]
    if not request.audit_entries:
        story.append(_p("No audit trail entries recorded for this document pair."))
        return story

    rows: list = [["Topic", "Decision", "Reviewer", "Decided"]]
    for entry in request.audit_entries:
        rows.append(
            [
                _p(entry.topic or entry.risk_rating),
                _p(entry.decision.upper()),
                _p(entry.reviewer or "--"),
                _p(entry.decided_at or "pending"),
            ]
        )
    table = Table(rows, colWidths=[2.0 * inch, 1.1 * inch, 1.3 * inch, 2.1 * inch], repeatRows=1)
    table.setStyle(_TABLE_STYLE)
    story.append(table)
    return story


def generate_report_pdf(request: ReportRequest) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        topMargin=0.85 * inch,
        bottomMargin=0.85 * inch,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
    )

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    story: list = [
        _p("Contract & SOW Risk Analysis Report", _title_style),
        _p(f"{request.msa_filename}  vs  {request.sow_filename}", _subtitle_style),
        _p(f"Generated {generated_at}", _meta_style),
    ]
    story.extend(_risk_summary_section(request))
    story.extend(_contradiction_details_section(request))
    story.extend(_obligations_section(request))
    story.extend(_audit_trail_section(request))
    story.append(
        _p(
            "This report includes AI-assisted findings (contradiction detection, confidence scores) alongside "
            "deterministic structural findings (dependency graph, missing references, obligations). AI-assisted "
            "findings are decision support, not legal conclusions -- each requires human review and an explicit "
            "audit trail decision before being relied upon.",
            _disclaimer_style,
        )
    )

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
