from __future__ import annotations

import re

from fastapi import APIRouter, Response

from app.models.report import ReportRequest
from app.services.report_service import generate_report_pdf

router = APIRouter()

_UNSAFE_FILENAME_CHARS_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def _safe_filename(msa_filename: str, sow_filename: str) -> str:
    base = f"{msa_filename}_vs_{sow_filename}_risk_report.pdf"
    return _UNSAFE_FILENAME_CHARS_RE.sub("_", base)


@router.post("/generate")
def generate(payload: ReportRequest) -> Response:
    pdf_bytes = generate_report_pdf(payload)
    filename = _safe_filename(payload.msa_filename, payload.sow_filename)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
