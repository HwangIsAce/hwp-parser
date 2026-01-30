"""
Document → 텍스트 / 마크다운 / JSON 변환.

- document_to_text: 문단·표 텍스트만 이어붙임
- document_to_markdown: 글자 모양(크기/굵기) 반영, 표는 마크다운 테이블
- document_to_json: JSON 직렬화용 dict
"""

import json
from typing import Any, Dict, List, Union

from ..model.document import Document, Section
from ..model.paragraph import Paragraph, Run
from ..model.table import Cell, Table


def document_to_text(doc: Document) -> str:
    """문서 전체를 평문 텍스트로 반환 (문단 + 표 셀 텍스트)."""
    parts: List[str] = []
    for sec in doc.sections:
        for p in sec.paragraphs:
            if p.text.strip():
                parts.append(p.text.strip())
        for t in sec.tables:
            for row in t.cells:
                for cell in row:
                    if cell.text.strip():
                        parts.append(cell.text.strip())
    return "\n".join(parts)


def _run_to_markdown(run: Run) -> str:
    """런 텍스트를 글자 모양에 따라 마크다운으로."""
    text = run.text or ""
    if not text.strip():
        return text
    shape = run.char_shape
    if shape is None:
        return text
    if shape.font_size >= 28:
        return f"# {text}"
    if shape.font_size >= 20:
        return f"## {text}"
    if shape.font_size >= 14:
        return f"### {text}"
    if shape.bold:
        return f"**{text}**"
    return text


def _paragraph_to_markdown(p: Paragraph) -> str:
    """문단을 마크다운으로 (런별 글자 모양 적용)."""
    if not p.runs:
        return ""
    parts = [_run_to_markdown(r) for r in p.runs]
    return "".join(parts).strip()


def _table_to_markdown(t: Table) -> str:
    """표를 마크다운 테이블 문자열로."""
    if not t.cells or not t.cells[0]:
        return ""
    rows = t.rows
    cols = t.cols
    lines: List[str] = []
    for r in range(rows):
        if r >= len(t.cells):
            break
        row_cells = []
        for c in range(cols):
            if c >= len(t.cells[r]):
                row_cells.append("")
            else:
                cell = t.cells[r][c]
                cell_text = cell.text.replace("\n", " ").strip()
                row_cells.append(cell_text)
        lines.append("| " + " | ".join(row_cells) + " |")
    if not lines:
        return ""
    sep = "| " + " | ".join(["---"] * len(lines[0].split("|")[1:-1])) + " |"
    return lines[0] + "\n" + sep + "\n" + "\n".join(lines[1:])


def document_to_markdown(doc: Document) -> str:
    """문서를 마크다운 문자열로 변환 (글자 모양 → 제목/볼드, 표 → 마크다운 테이블)."""
    parts: List[str] = []
    for sec in doc.sections:
        for p in sec.paragraphs:
            md = _paragraph_to_markdown(p)
            if md:
                parts.append(md)
                parts.append("")
        for t in sec.tables:
            md = _table_to_markdown(t)
            if md:
                parts.append(md)
                parts.append("")
    return "\n".join(parts).strip()


def _paragraph_to_dict(p: Paragraph) -> Dict[str, Any]:
    return {
        "text": p.text,
        "para_shape_id": p.para_shape_id,
        "page_break": p.page_break,
        "runs": [
            {
                "text": r.text,
                "char_shape_id": r.char_shape_id,
            }
            for r in p.runs
        ],
    }


def _cell_to_dict(cell: Cell) -> Dict[str, Any]:
    return {
        "text": cell.text,
        "row": cell.row,
        "col": cell.col,
        "rowspan": cell.rowspan,
        "colspan": cell.colspan,
        "contents": [
            _paragraph_to_dict(c) if isinstance(c, Paragraph) else _table_to_dict(c)
            for c in cell.contents
        ],
    }


def _table_to_dict(t: Table) -> Dict[str, Any]:
    return {
        "rows": t.rows,
        "cols": t.cols,
        "cells": [
            [_cell_to_dict(cell) for cell in row]
            for row in t.cells
        ],
    }


def _section_to_dict(sec: Section) -> Dict[str, Any]:
    return {
        "paragraphs": [_paragraph_to_dict(p) for p in sec.paragraphs],
        "tables": [_table_to_dict(t) for t in sec.tables],
    }


def document_to_dict(doc: Document) -> Dict[str, Any]:
    """Document를 JSON 직렬화 가능한 dict로 변환."""
    return {
        "version": doc.version,
        "compressed": doc.compressed,
        "encrypted": doc.encrypted,
        "sections": [_section_to_dict(sec) for sec in doc.sections],
    }


def document_to_json(doc: Document, indent: Union[None, int] = 2) -> str:
    """Document를 JSON 문자열로 변환."""
    return json.dumps(document_to_dict(doc), ensure_ascii=False, indent=indent)
