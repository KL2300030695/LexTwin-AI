"""DOCX parsing via python-docx.

Note: DOCX has no native pagination without a rendering engine. We approximate
page numbers by counting explicit hard page breaks (w:br type="page") in the
run stream; a document with no explicit page breaks is treated as a single
page. PDFs (see pdf_parser.py) give exact page numbers and are the preferred
format for page-cited risk reports.
"""
from __future__ import annotations

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.models.schema import DocType, ParsedDocument, TableModel
from app.parsers.structure import Line, TableAnchor, build_document


def _iter_block_items(document: Document):
    body = document.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield Table(child, document)


def _has_page_break(paragraph: Paragraph) -> bool:
    return len(paragraph._element.xpath('.//w:br[@w:type="page"]')) > 0


def parse_docx(file_path: str, doc_id: str, filename: str, doc_type: DocType) -> ParsedDocument:
    document = Document(file_path)
    lines: list[Line] = []
    anchors: list[TableAnchor] = []
    table_counter = 0
    page = 1

    for block in _iter_block_items(document):
        if isinstance(block, Paragraph):
            if _has_page_break(block):
                page += 1
            text = block.text.strip()
            if text:
                lines.append(Line(text=text, page=page))
        else:
            table_counter += 1
            table_id = f"{doc_id}-table-{table_counter}"
            rows = [[cell.text.strip() for cell in row.cells] for row in block.rows]
            header = rows[0] if rows else None
            table_model = TableModel(id=table_id, page=page, rows=rows, header=header)
            anchors.append(TableAnchor(after_line_index=len(lines) - 1, table=table_model))

    return build_document(doc_id, filename, doc_type, lines, anchors, page_count=page)
