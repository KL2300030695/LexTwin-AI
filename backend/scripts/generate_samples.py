"""Generates two synthetic sample contracts (MSA + SOW) as real PDFs, with
three intentional issues baked in for testing later phases:

  1. Circular reference: MSA Section 6.3 <-> MSA Section 9.1 reference each other.
  2. Missing exhibit: MSA Section 4.3 references "Exhibit C" which is never
     included in either document (Exhibit A and Exhibit B ARE included).
  3. MSA/SOW contradiction: MSA Section 5.1 says payment due in 45 days;
     SOW Section 3.3 says payment due in 15 days.

Run with:  python scripts/generate_samples.py
Writes samples/msa_sample.pdf and samples/sow_sample.pdf (repo-root/samples).
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

SAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

styles = getSampleStyleSheet()
h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=13, spaceBefore=14, spaceAfter=6, keepWithNext=1)
h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=11, spaceBefore=10, spaceAfter=4, keepWithNext=1)
h3 = ParagraphStyle("H3", parent=styles["Heading3"], fontSize=10, spaceBefore=8, spaceAfter=4, keepWithNext=1)
body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9.5, leading=13, spaceAfter=6)
title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=16, spaceAfter=18)

TABLE_STYLE = TableStyle(
    [
        ("GRID", (0, 0), (-1, -1), 0.75, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
)


def build_msa():
    doc = SimpleDocTemplate(
        str(SAMPLES_DIR / "msa_sample.pdf"),
        pagesize=LETTER,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
    )
    story = []
    P = lambda text, style=body: story.append(Paragraph(text, style))

    P("MASTER SERVICE AGREEMENT", title_style)
    P(
        "This Master Service Agreement (the &quot;Agreement&quot;) is entered into by and between "
        "Northwind Client Corp. (&quot;Client&quot;) and Vantage Solutions LLC (&quot;Provider&quot;), "
        "effective as of January 15, 2026."
    )

    P("1. DEFINITIONS", h1)
    P('1.1 "Confidential Information" Definition', h2)
    P(
        "Confidential Information means any non-public information disclosed by either party, "
        "whether in written, oral, or electronic form, that is designated confidential or that "
        "reasonably should be understood to be confidential given the nature of the information."
    )
    P('1.2 "Deliverable" Definition', h2)
    P(
        "Deliverable means any work product, report, software, or other output that Provider is "
        "obligated to create and deliver to Client under this Agreement or any Statement of Work."
    )

    P("2. TERM AND TERMINATION", h1)
    P("2.1 Initial Term", h2)
    P(
        "This Agreement commences on the Effective Date and continues for an initial term of "
        "three years, unless terminated earlier in accordance with this Section 2."
    )
    P("2.2 Termination for Cause", h2)
    P(
        "Either party may terminate this Agreement upon written notice if the other party commits "
        "a material breach and fails to cure such breach within thirty days after receiving written "
        "notice describing the breach in reasonable detail."
    )
    P("2.3 Termination for Convenience", h2)
    P(
        "Notwithstanding Section 2.2, either party may terminate this Agreement for convenience, "
        "without cause, upon ninety days prior written notice to the other party."
    )

    P("3. SCOPE OF SERVICES AND STATEMENTS OF WORK", h1)
    P("3.1 Statements of Work", h2)
    P(
        "Provider shall perform services described in one or more Statements of Work ('SOW') "
        "executed by both parties and incorporated into this Agreement by reference."
    )
    P("3.2 Order of Precedence", h2)
    P(
        "If a conflict exists between the terms of this Agreement and a Statement of Work, the "
        "terms of this Agreement shall govern, except with respect to project-specific fees and "
        "milestone schedules, which shall be governed by the applicable Statement of Work."
    )

    P("4. SERVICE LEVELS", h1)
    P("4.1 Performance Standards", h2)
    P(
        "Provider shall perform the Services in a professional and workmanlike manner consistent "
        "with generally accepted industry standards."
    )
    P("4.2 Service Level Credits", h2)
    P("The following service credit tiers apply based on measured monthly uptime:")
    story.append(
        Table(
            [
                ["Uptime Tier", "Monthly Uptime %", "Service Credit"],
                ["Tier 1", "99.9% or greater", "0%"],
                ["Tier 2", "99.0% - 99.89%", "5% of monthly fees"],
                ["Tier 3", "95.0% - 98.99%", "10% of monthly fees"],
                ["Tier 4", "Below 95.0%", "25% of monthly fees"],
            ],
            colWidths=[1.6 * inch, 2.0 * inch, 2.0 * inch],
            style=TABLE_STYLE,
        )
    )
    story.append(Spacer(1, 10))
    P("4.3 Detailed SLA Terms", h2)
    P(
        "Additional measurement methodology, exclusions, and reporting cadence are set forth in "
        "Exhibit C (Service Level Agreement) attached hereto."
    )

    story.append(PageBreak())

    P("5. FEES AND PAYMENT TERMS", h1)
    P("5.1 Invoicing and Payment", h2)
    P(
        "Provider shall invoice Client monthly in arrears. Client shall pay all undisputed "
        "invoices within forty-five days of receipt of a correct invoice."
    )
    P("5.2 Late Payment Penalty", h2)
    P("Undisputed invoices not paid when due accrue a late penalty as follows:")
    story.append(
        Table(
            [
                ["Days Past Due", "Penalty Rate"],
                ["1-15 days", "1.0% of overdue amount"],
                ["16-30 days", "2.5% of overdue amount"],
                ["31+ days", "5.0% of overdue amount, plus suspension rights"],
            ],
            colWidths=[2.2 * inch, 3.4 * inch],
            style=TABLE_STYLE,
        )
    )
    story.append(Spacer(1, 10))
    P("5.3 Suspension for Non-Payment", h2)
    P(
        "Provider may suspend Services if an invoice remains unpaid more than thirty days after "
        "the due date described in Section 5.1."
    )

    P("6. LIMITATION OF LIABILITY", h1)
    P("6.1 Liability Cap", h2)
    P(
        "Except as otherwise expressly provided elsewhere in this Agreement, each party's total "
        "aggregate liability arising out of this Agreement shall not exceed the fees paid in the "
        "twelve months preceding the claim."
    )
    P("6.2 Exclusion of Consequential Damages", h2)
    P(
        "Neither party shall be liable for indirect, incidental, special, or consequential "
        "damages, even if advised of the possibility of such damages."
    )
    P("6.3 Liability Carve-Outs", h2)
    P(
        "The limitations described in Section 6.1 shall not apply to claims arising under the "
        "indemnification obligations set forth in Section 9.1."
    )

    P("7. CONFIDENTIALITY", h1)
    P("7.1 Confidential Information Obligations", h2)
    P(
        "Each party shall protect the other party's Confidential Information using at least the "
        "same degree of care it uses for its own confidential information, and in no event less "
        "than reasonable care."
    )
    P("7.2 Exceptions", h2)
    P(
        "Confidential Information does not include information that is or becomes publicly "
        "available through no fault of the receiving party."
    )

    P("8. INTELLECTUAL PROPERTY", h1)
    P("8.1 Ownership of Pre-Existing IP", h2)
    P("Each party retains all right, title, and interest in its intellectual property existing prior to this Agreement.")
    P("8.2 Ownership of Work Product", h2)
    P("Subject to Section 8.1, Provider assigns to Client all right, title, and interest in Deliverables upon full payment.")

    story.append(PageBreak())

    P("9. INDEMNIFICATION", h1)
    P("9.1 General Indemnification", h2)
    P(
        "Each party shall indemnify, defend, and hold harmless the other party from third-party "
        "claims arising from its gross negligence or willful misconduct. Each party's obligations "
        "under this Section 9.1 are subject to the limitation of liability set forth in Section 6.3."
    )

    P("10. GOVERNING LAW AND DISPUTE RESOLUTION", h1)
    P("10.1 Governing Law", h2)
    P("This Agreement is governed by the laws of the State of Delaware, without regard to conflict of law principles.")
    P("10.2 Dispute Resolution", h2)
    P("The parties shall attempt in good faith to resolve any dispute through escalation to senior management before initiating formal proceedings.")

    P("11. GENERAL PROVISIONS", h1)
    P("11.1 Assignment", h2)
    P("Neither party may assign this Agreement without the prior written consent of the other party, not to be unreasonably withheld.")
    P("11.2 Entire Agreement", h2)
    P(
        "This Agreement, together with Exhibit A (Approved Subcontractors) and Exhibit B (Data "
        "Processing Addendum), constitutes the entire agreement between the parties regarding its subject matter."
    )

    story.append(PageBreak())

    P("EXHIBIT A APPROVED SUBCONTRACTORS", h1)
    P("The following subcontractors are pre-approved for use by Provider in performing the Services:")
    story.append(
        Table(
            [
                ["Subcontractor", "Role", "Approved Since"],
                ["Cascade Data Systems", "Infrastructure hosting", "2024-03-01"],
                ["BrightPath QA Ltd.", "Quality assurance testing", "2024-06-15"],
            ],
            colWidths=[2.2 * inch, 2.4 * inch, 1.4 * inch],
            style=TABLE_STYLE,
        )
    )
    story.append(Spacer(1, 10))

    P("EXHIBIT B DATA PROCESSING ADDENDUM", h1)
    P(
        "This Exhibit B governs the processing of personal data by Provider on behalf of Client "
        "in connection with the Services, including applicable data security and breach "
        "notification obligations, each in accordance with applicable data protection law."
    )

    doc.build(story)
    print(f"Wrote {SAMPLES_DIR / 'msa_sample.pdf'}")


def build_sow():
    doc = SimpleDocTemplate(
        str(SAMPLES_DIR / "sow_sample.pdf"),
        pagesize=LETTER,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
    )
    story = []
    P = lambda text, style=body: story.append(Paragraph(text, style))

    P("STATEMENT OF WORK #1 CLOUD MIGRATION SERVICES", title_style)
    P(
        "This Statement of Work is issued under and governed by the Master Service Agreement "
        "between Northwind Client Corp. and Vantage Solutions LLC, effective January 15, 2026."
    )

    P("1. PURPOSE AND SCOPE", h1)
    P("1.1 Project Overview", h2)
    P(
        "Provider will migrate Client's on-premises application workloads to a cloud "
        "infrastructure environment, including assessment, migration execution, and post-migration validation."
    )
    P("1.2 Deliverables", h2)
    story.append(
        Table(
            [
                ["Deliverable", "Description", "Due Date"],
                ["Migration Assessment Report", "Readiness assessment of workloads", "2026-02-15"],
                ["Migration Runbook", "Step-by-step cutover execution plan", "2026-03-01"],
                ["Post-Migration Validation Report", "Post-cutover performance validation", "2026-04-30"],
            ],
            colWidths=[1.9 * inch, 3.1 * inch, 1.0 * inch],
            style=TABLE_STYLE,
        )
    )
    story.append(Spacer(1, 10))

    P("2. TERM", h1)
    P("2.1 Period of Performance", h2)
    P("This Statement of Work is effective from February 1, 2026 through April 30, 2026, unless extended by written amendment.")

    story.append(PageBreak())

    P("3. FEES AND PAYMENT TERMS", h1)
    P("3.1 Fixed Fee", h2)
    P("The total fixed fee for the Services described in this Statement of Work is $250,000, payable per the milestone schedule in Section 3.2.")
    P("3.2 Milestone Payment Schedule", h2)
    story.append(
        Table(
            [
                ["Milestone", "% of Fee", "Amount"],
                ["Migration Assessment Report accepted", "30%", "$75,000"],
                ["Migration Runbook accepted", "30%", "$75,000"],
                ["Post-Migration Validation Report accepted", "40%", "$100,000"],
            ],
            colWidths=[2.6 * inch, 1.2 * inch, 2.2 * inch],
            style=TABLE_STYLE,
        )
    )
    story.append(Spacer(1, 10))
    P("3.3 Invoice Terms", h2)
    P("Provider shall invoice Client upon acceptance of each milestone. Client shall pay invoices within fifteen days of receipt.")

    P("4. SERVICE LEVELS", h1)
    P("4.1 Project-Specific SLAs", h2)
    P(
        "The uptime tiers and service credits described in Section 4.2 of the Master Service "
        "Agreement apply to the migrated production environment beginning on the cutover date."
    )

    P("5. STAFFING", h1)
    P("5.1 Key Personnel", h2)
    P("Provider shall assign a dedicated Migration Lead and Cloud Architect for the duration of this engagement.")
    P("5.2 Subcontractors", h2)
    P("Provider may use subcontractors as approved in Exhibit A of the Master Service Agreement.")

    story.append(PageBreak())

    P("6. CHANGE MANAGEMENT", h1)
    P("6.1 Change Order Process", h2)
    P(
        "Any change to the scope, fees, or schedule described in this Statement of Work requires "
        "a written change order signed by both parties."
    )

    P("7. ACCEPTANCE CRITERIA", h1)
    P("7.1 Acceptance Testing", h2)
    P("Client shall have ten business days to review each Deliverable and either accept it or provide written comments.")
    P("7.2 Deliverable Sign-off", h2)
    P(
        "Notwithstanding Section 6.1, minor deliverable adjustments identified during acceptance "
        "testing under Section 7.1 do not require a formal change order."
    )

    doc.build(story)
    print(f"Wrote {SAMPLES_DIR / 'sow_sample.pdf'}")


if __name__ == "__main__":
    build_msa()
    build_sow()
