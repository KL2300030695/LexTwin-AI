"""PDF parsing via PyMuPDF: extracts text lines (with true page numbers) and
tables in reading order, then hands off to structure.build_document()."""
from __future__ import annotations

import fitz  # PyMuPDF

from app.models.schema import DocType, ParsedDocument, TableModel
from app.parsers.structure import Line, TableAnchor, build_document


def parse_pdf(file_path: str, doc_id: str, filename: str, doc_type: DocType) -> ParsedDocument:
    doc = fitz.open(file_path)
    lines: list[Line] = []
    anchors: list[TableAnchor] = []
    table_counter = 0

    for page_index in range(len(doc)):
        page = doc[page_index]
        page_num = page_index + 1

        text_blocks = [b for b in page.get_text("blocks") if b[6] == 0]  # type 0 = text block

        try:
            tables = list(page.find_tables().tables)
        except Exception:
            tables = []

        # Text blocks inside a detected table's bbox are dropped here -- their
        # content is captured via the table's own row extraction instead, to
        # avoid emitting each cell twice (once as a loose line, once as a row).
        def _inside_a_table(block) -> bool:
            cx, cy = (block[0] + block[2]) / 2, (block[1] + block[3]) / 2
            return any(t.bbox[0] <= cx <= t.bbox[2] and t.bbox[1] <= cy <= t.bbox[3] for t in tables)

        text_blocks = [b for b in text_blocks if not _inside_a_table(b)]

        # Merge text blocks and tables into single top-to-bottom reading order per page.
        items: list[tuple[float, str, object]] = []
        for b in text_blocks:
            items.append((b[1], "text", b[4]))
        for t in tables:
            items.append((t.bbox[1], "table", t))
        items.sort(key=lambda it: it[0])

        for _, kind, payload in items:
            if kind == "text":
                is_first = True
                for raw_line in str(payload).split("\n"):
                    line_text = raw_line.strip()
                    if line_text:
                        lines.append(Line(text=line_text, page=page_num, is_block_start=is_first))
                        is_first = False
            else:
                table_counter += 1
                table_id = f"{doc_id}-table-{table_counter}"
                rows = [[(c or "").strip() for c in row] for row in payload.extract()]
                header = rows[0] if rows else None
                table_model = TableModel(id=table_id, page=page_num, rows=rows, header=header)
                anchors.append(TableAnchor(after_line_index=len(lines) - 1, table=table_model))

    page_count = len(doc)
    doc.close()
    return build_document(doc_id, filename, doc_type, lines, anchors, page_count)
