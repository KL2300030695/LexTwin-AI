"""Generates three additional synthetic sample MSA/SOW pairs as real PDFs,
each seeded with a DIFFERENT category of issue than the original
samples/msa_sample.pdf + sow_sample.pdf pair (circular reference + missing
exhibit + payment contradiction, all in one pair). This script keeps each
new pair focused on one issue family so each risk-flag type has its own
clean demo case:

  1. msa_override_sample.pdf / sow_override_sample.pdf
     - Override conflict: MSA Section 5.2 <-> MSA Section 8.1 each say
       "Notwithstanding Section <other>", forming a cycle of
       notwithstanding_override edges (severity: override_conflict).
     - A general override: a bare "Notwithstanding anything to the
       contrary herein" with no specific target section.
     - A Liability contradiction: MSA's fee-based liability cap vs the
       SOW's flat-dollar cap for the same engagement.

  2. msa_clean_sample.pdf / sow_clean_sample.pdf
     - Zero seeded issues: every reference resolves, payment terms agree
       (30 days on both sides), no circular references, no contradictions.
       Useful for demoing what a "safe to sign" result looks like.

  3. msa_missing_sample.pdf / sow_missing_sample.pdf
     - Missing-reference guardrail, several times over: Exhibit D,
       Appendix 2, and Schedule 1 are all referenced but never included
       in either document. Exhibit A IS included, as a contrast case
       showing the guardrail only fires on what's actually absent.

Run with:  python scripts/generate_more_samples.py
Writes six PDFs into samples/ (repo-root/samples), alongside the existing
msa_sample.pdf / sow_sample.pdf.
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


def _doc(filename: str) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        str(SAMPLES_DIR / filename),
        pagesize=LETTER,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
    )


# ─────────────────────────────────────────────────────────────────────────
# Pair 1: override conflict + general override + liability contradiction
# ─────────────────────────────────────────────────────────────────────────

def build_msa_override():
    doc = _doc("msa_override_sample.pdf")
    story = []
    P = lambda text, style=body: story.append(Paragraph(text, style))

    P("MASTER SOFTWARE LICENSE AND SUPPORT AGREEMENT", title_style)
    P(
        "This Master Software License and Support Agreement (the &quot;Agreement&quot;) is entered "
        "into by and between Redshore Financial Group (&quot;Client&quot;) and Alderbrook Systems Inc. "
        "(&quot;Provider&quot;), effective as of March 1, 2026."
    )

    P("1. DEFINITIONS", h1)
    P('1.1 "Software" Definition', h2)
    P("Software means Provider's proprietary risk-modeling platform, including all updates and patches provided under this Agreement.")
    P('1.2 "Support Services" Definition', h2)
    P("Support Services means the maintenance, bug-fix, and help-desk services described in Section 6.")

    P("2. TERM AND TERMINATION", h1)
    P("2.1 Initial Term", h2)
    P("This Agreement commences on the Effective Date and continues for an initial term of two years.")
    P("2.2 Termination for Insolvency", h2)
    P(
        "Notwithstanding anything to the contrary herein, Client may terminate this Agreement "
        "immediately upon written notice if Provider becomes insolvent, files for bankruptcy "
        "protection, or ceases operations in the ordinary course of business."
    )

    P("3. LICENSE GRANT", h1)
    P("3.1 Scope of License", h2)
    P("Provider grants Client a non-exclusive, non-transferable license to use the Software solely for Client's internal business operations.")
    P("3.2 Restrictions", h2)
    P("Client shall not sublicense, reverse engineer, or resell the Software without Provider's prior written consent.")

    story.append(PageBreak())

    P("4. FEES AND PAYMENT TERMS", h1)
    P("4.1 License Fees", h2)
    P("Client shall pay all license and support fees within thirty days of receipt of a correct invoice.")

    P("5. LIABILITY", h1)
    P("5.1 Liability Cap", h2)
    P(
        "Except as otherwise expressly provided elsewhere in this Agreement, each party's total "
        "aggregate liability arising out of this Agreement shall not exceed the fees paid in the "
        "twelve months preceding the claim."
    )
    P("5.2 Liability Carve-Out for Confidentiality Breaches", h2)
    P(
        "Notwithstanding Section 8.1, the limitation of liability described in Section 5.1 shall "
        "not apply to damages arising from a breach of the confidentiality obligations."
    )

    P("6. SUPPORT SERVICES", h1)
    P("6.1 Support Levels", h2)
    P("Provider shall respond to Client support requests within the response times set forth in the applicable Statement of Work.")

    story.append(PageBreak())

    P("7. INTELLECTUAL PROPERTY", h1)
    P("7.1 Ownership", h2)
    P("Provider retains all right, title, and interest in and to the Software, including all modifications and derivative works.")

    P("8. CONFIDENTIALITY", h1)
    P("8.1 Confidentiality Obligations", h2)
    P(
        "Each party shall protect the other party's confidential information using at least "
        "reasonable care. Notwithstanding Section 5.2, damages for a confidentiality breach "
        "remain subject to the general limitation of liability for indirect or consequential losses."
    )

    P("9. GOVERNING LAW", h1)
    P("9.1 Governing Law", h2)
    P("This Agreement is governed by the laws of the State of New York, without regard to conflict of law principles.")

    doc.build(story)
    print(f"Wrote {SAMPLES_DIR / 'msa_override_sample.pdf'}")


def build_sow_override():
    doc = _doc("sow_override_sample.pdf")
    story = []
    P = lambda text, style=body: story.append(Paragraph(text, style))

    P("STATEMENT OF WORK #1 ENTERPRISE PLATFORM DEPLOYMENT", title_style)
    P(
        "This Statement of Work is issued under and governed by the Master Software License and "
        "Support Agreement between Redshore Financial Group and Alderbrook Systems Inc., effective March 1, 2026."
    )

    P("1. SCOPE", h1)
    P("1.1 Project Overview", h2)
    P("Provider will deploy and configure the Software across Client's production environment, including data migration and user training.")

    P("2. TERM", h1)
    P("2.1 Period of Performance", h2)
    P("This Statement of Work is effective from March 15, 2026 through July 15, 2026.")

    story.append(PageBreak())

    P("3. FEES AND PAYMENT TERMS", h1)
    P("3.1 Deployment Fee", h2)
    P("The total fee for deployment services is $180,000, invoiced in three equal milestone payments.")
    P("3.2 Invoice Terms", h2)
    P("Client shall pay all invoices within thirty days of receipt, consistent with the payment terms of the Master Service Agreement.")

    P("4. LIABILITY", h1)
    P("4.1 Liability Cap", h2)
    P(
        "Notwithstanding anything in the Master Service Agreement to the contrary, Provider's "
        "aggregate liability under this Statement of Work shall not exceed $50,000, regardless of "
        "the fees actually paid."
    )

    P("5. SERVICE LEVELS", h1)
    P("5.1 Support Response Times", h2)
    P("Provider shall acknowledge critical support tickets within two business hours and provide a resolution plan within one business day.")

    story.append(PageBreak())

    P("6. ACCEPTANCE CRITERIA", h1)
    P("6.1 Go-Live Acceptance", h2)
    P("Client shall have five business days following go-live to identify and report critical defects for remediation at no additional cost.")

    doc.build(story)
    print(f"Wrote {SAMPLES_DIR / 'sow_override_sample.pdf'}")


# ─────────────────────────────────────────────────────────────────────────
# Pair 2: clean pair, zero seeded issues
# ─────────────────────────────────────────────────────────────────────────

def build_msa_clean():
    doc = _doc("msa_clean_sample.pdf")
    story = []
    P = lambda text, style=body: story.append(Paragraph(text, style))

    P("MASTER CONSULTING SERVICES AGREEMENT", title_style)
    P(
        "This Master Consulting Services Agreement (the &quot;Agreement&quot;) is entered into by "
        "and between Fieldstone Retail Group (&quot;Client&quot;) and Meridian Advisory Partners "
        "(&quot;Provider&quot;), effective as of April 1, 2026."
    )

    P("1. DEFINITIONS", h1)
    P('1.1 "Deliverable" Definition', h2)
    P("Deliverable means any report, analysis, or recommendation Provider is obligated to create and deliver to Client under a Statement of Work.")

    P("2. TERM AND TERMINATION", h1)
    P("2.1 Initial Term", h2)
    P("This Agreement commences on the Effective Date and continues for an initial term of one year.")
    P("2.2 Termination for Convenience", h2)
    P("Either party may terminate this Agreement for convenience upon sixty days prior written notice to the other party.")

    story.append(PageBreak())

    P("3. SCOPE OF SERVICES", h1)
    P("3.1 Statements of Work", h2)
    P("Provider shall perform services described in one or more Statements of Work executed by both parties and incorporated into this Agreement by reference.")

    P("4. FEES AND PAYMENT TERMS", h1)
    P("4.1 Invoicing and Payment", h2)
    P("Provider shall invoice Client monthly in arrears. Client shall pay all undisputed invoices within thirty days of receipt of a correct invoice.")

    P("5. LIABILITY", h1)
    P("5.1 Liability Cap", h2)
    P("Each party's total aggregate liability arising out of this Agreement shall not exceed the fees paid in the six months preceding the claim.")

    story.append(PageBreak())

    P("6. CONFIDENTIALITY", h1)
    P("6.1 Confidentiality Obligations", h2)
    P("Each party shall protect the other party's confidential information using at least reasonable care.")

    P("7. INTELLECTUAL PROPERTY", h1)
    P("7.1 Ownership of Work Product", h2)
    P("Provider assigns to Client all right, title, and interest in Deliverables upon full payment.")

    P("8. GOVERNING LAW", h1)
    P("8.1 Governing Law", h2)
    P("This Agreement is governed by the laws of the State of Illinois, without regard to conflict of law principles.")

    story.append(PageBreak())

    P("EXHIBIT A RATE CARD", h1)
    P("The following hourly rates apply to Services performed under any Statement of Work issued pursuant to this Agreement:")
    story.append(
        Table(
            [
                ["Role", "Hourly Rate"],
                ["Engagement Partner", "$450"],
                ["Senior Consultant", "$275"],
                ["Analyst", "$150"],
            ],
            colWidths=[3.0 * inch, 2.0 * inch],
            style=TABLE_STYLE,
        )
    )

    doc.build(story)
    print(f"Wrote {SAMPLES_DIR / 'msa_clean_sample.pdf'}")


def build_sow_clean():
    doc = _doc("sow_clean_sample.pdf")
    story = []
    P = lambda text, style=body: story.append(Paragraph(text, style))

    P("STATEMENT OF WORK #1 MARKET ENTRY STRATEGY CONSULTING", title_style)
    P(
        "This Statement of Work is issued under and governed by the Master Consulting Services "
        "Agreement between Fieldstone Retail Group and Meridian Advisory Partners, effective April 1, 2026."
    )

    P("1. SCOPE", h1)
    P("1.1 Project Overview", h2)
    P("Provider will conduct a market entry feasibility study for Client's expansion into two new regional markets.")
    P("1.2 Deliverables", h2)
    story.append(
        Table(
            [
                ["Deliverable", "Description", "Due Date"],
                ["Market Assessment Report", "Sizing and competitive landscape analysis", "2026-05-15"],
                ["Entry Strategy Recommendation", "Go-to-market plan and risk assessment", "2026-06-15"],
            ],
            colWidths=[2.0 * inch, 3.0 * inch, 1.0 * inch],
            style=TABLE_STYLE,
        )
    )
    story.append(Spacer(1, 10))

    P("2. TERM", h1)
    P("2.1 Period of Performance", h2)
    P("This Statement of Work is effective from April 15, 2026 through June 15, 2026.")

    story.append(PageBreak())

    P("3. FEES AND PAYMENT TERMS", h1)
    P("3.1 Fixed Fee", h2)
    P("The total fixed fee for the Services described in this Statement of Work is $120,000.")
    P("3.2 Invoice Terms", h2)
    P("Provider shall invoice Client upon acceptance of each deliverable. Client shall pay invoices within thirty days of receipt.")

    P("4. STAFFING", h1)
    P("4.1 Rates", h2)
    P("Services under this Statement of Work shall be billed at the hourly rates set forth in Exhibit A of the Master Service Agreement.")

    story.append(PageBreak())

    P("5. ACCEPTANCE CRITERIA", h1)
    P("5.1 Deliverable Sign-off", h2)
    P("Client shall have ten business days to review each Deliverable and either accept it or provide written comments.")

    doc.build(story)
    print(f"Wrote {SAMPLES_DIR / 'sow_clean_sample.pdf'}")


# ─────────────────────────────────────────────────────────────────────────
# Pair 3: missing-reference guardrail, several times over
# ─────────────────────────────────────────────────────────────────────────

def build_msa_missing():
    doc = _doc("msa_missing_sample.pdf")
    story = []
    P = lambda text, style=body: story.append(Paragraph(text, style))

    P("MASTER FACILITIES SERVICES AGREEMENT", title_style)
    P(
        "This Master Facilities Services Agreement (the &quot;Agreement&quot;) is entered into by "
        "and between Kestrel Property Holdings (&quot;Client&quot;) and Ombrewood Construction Group "
        "(&quot;Provider&quot;), effective as of May 1, 2026."
    )

    P("1. DEFINITIONS", h1)
    P('1.1 "Site" Definition', h2)
    P("Site means any Client-owned or leased facility identified in an applicable Statement of Work.")

    P("2. TERM AND TERMINATION", h1)
    P("2.1 Initial Term", h2)
    P("This Agreement commences on the Effective Date and continues for an initial term of eighteen months.")

    story.append(PageBreak())

    P("3. SCOPE OF SERVICES", h1)
    P("3.1 Site Specifications", h2)
    P(
        "Provider shall perform renovation and maintenance services as further detailed in Exhibit D "
        "(Site Specifications) attached hereto, covering each Site identified in the applicable "
        "Statement of Work."
    )

    P("4. FEES AND PAYMENT TERMS", h1)
    P("4.1 Invoicing and Payment", h2)
    P("Provider shall invoice Client monthly in arrears. Client shall pay all undisputed invoices within thirty days of receipt of a correct invoice.")

    story.append(PageBreak())

    P("5. SERVICE LEVELS", h1)
    P("5.1 Maintenance Schedule", h2)
    P(
        "Routine and preventative maintenance shall be performed in accordance with the schedule set "
        "forth in Appendix 2 (Maintenance Schedule) attached hereto."
    )

    P("6. LIABILITY", h1)
    P("6.1 Liability Cap", h2)
    P("Each party's total aggregate liability arising out of this Agreement shall not exceed the fees paid in the twelve months preceding the claim.")

    story.append(PageBreak())

    P("7. INSURANCE", h1)
    P("7.1 Coverage Requirements", h2)
    P(
        "Provider shall maintain insurance coverage of the types and minimum limits set forth in "
        "Schedule 1 (Insurance Requirements) attached hereto, for the duration of this Agreement."
    )

    P("8. APPROVED VENDORS", h1)
    P("8.1 Reference to Exhibit A", h2)
    P("Provider may engage the subcontractors identified in Exhibit A (Approved Vendors) without additional Client approval.")

    story.append(PageBreak())

    P("EXHIBIT A APPROVED VENDORS", h1)
    P("The following subcontractors are pre-approved for use by Provider in performing the Services:")
    story.append(
        Table(
            [
                ["Vendor", "Trade", "Approved Since"],
                ["Ironclad Electrical Co.", "Electrical", "2025-01-10"],
                ["Summit HVAC Services", "HVAC", "2025-04-22"],
            ],
            colWidths=[2.2 * inch, 2.2 * inch, 1.6 * inch],
            style=TABLE_STYLE,
        )
    )

    doc.build(story)
    print(f"Wrote {SAMPLES_DIR / 'msa_missing_sample.pdf'}")


def build_sow_missing():
    doc = _doc("sow_missing_sample.pdf")
    story = []
    P = lambda text, style=body: story.append(Paragraph(text, style))

    P("STATEMENT OF WORK #1 HEADQUARTERS RENOVATION", title_style)
    P(
        "This Statement of Work is issued under and governed by the Master Facilities Services "
        "Agreement between Kestrel Property Holdings and Ombrewood Construction Group, effective May 1, 2026."
    )

    P("1. SCOPE", h1)
    P("1.1 Project Overview", h2)
    P(
        "Provider will renovate Client's headquarters office space in accordance with the "
        "specifications described in Exhibit D of the Master Service Agreement."
    )

    P("2. TERM", h1)
    P("2.1 Period of Performance", h2)
    P("This Statement of Work is effective from May 15, 2026 through September 15, 2026.")

    story.append(PageBreak())

    P("3. FEES AND PAYMENT TERMS", h1)
    P("3.1 Fixed Fee", h2)
    P("The total fixed fee for the Services described in this Statement of Work is $420,000.")
    P("3.2 Invoice Terms", h2)
    P("Provider shall invoice Client upon completion of each phase. Client shall pay invoices within thirty days of receipt.")

    P("4. STAFFING", h1)
    P("4.1 Subcontractors", h2)
    P("Provider may use subcontractors as approved in Exhibit A (Approved Vendors) of the Master Service Agreement.")

    story.append(PageBreak())

    P("5. ACCEPTANCE CRITERIA", h1)
    P("5.1 Phase Sign-off", h2)
    P("Client shall have ten business days to inspect each completed phase and either accept it or provide written comments.")

    doc.build(story)
    print(f"Wrote {SAMPLES_DIR / 'sow_missing_sample.pdf'}")


if __name__ == "__main__":
    build_msa_override()
    build_sow_override()
    build_msa_clean()
    build_sow_clean()
    build_msa_missing()
    build_sow_missing()
