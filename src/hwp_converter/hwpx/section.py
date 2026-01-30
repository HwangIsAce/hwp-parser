"""
HWPX Section XML 파싱 (Contents/section{N}.xml).

- body / sec / p / t / tbl / tr / tc 등 로컬 이름으로 요소 탐색
- 문단·표 → model.Paragraph, model.Table
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple, Union

from ..model.paragraph import Paragraph, Run
from ..model.shape import CharShape
from ..model.table import Cell, Table


def _local_name(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _text_of(elem: ET.Element) -> str:
    """요소의 직접 텍스트 + 자식 t/text 노드 합침."""
    if elem.text and elem.text.strip():
        return elem.text.strip()
    parts: List[str] = []
    for child in elem:
        local = _local_name(child.tag).lower()
        if local in ("t", "text"):
            if child.text:
                parts.append(child.text)
            if child.tail:
                parts.append(child.tail)
        else:
            parts.append(_text_of(child))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts).strip()


def _parse_paragraph(elem: ET.Element, char_shapes: Optional[Dict[int, CharShape]] = None) -> Paragraph:
    """단일 p/paragraph 요소 → Paragraph (런 1개: 전체 텍스트)."""
    text = _text_of(elem)
    run = Run(text=text)
    return Paragraph(runs=[run])


def _parse_table(elem: ET.Element, char_shapes: Optional[Dict[int, CharShape]] = None) -> Optional[Table]:
    """tbl/table 요소 → Table. tr → 행, tc → 셀, 셀 안 p/tbl 재귀."""
    rows_elems: List[ET.Element] = []
    for child in elem:
        local = _local_name(child.tag).lower()
        if local in ("tr", "row"):
            rows_elems.append(child)
    if not rows_elems:
        return None
    grid: List[List[Cell]] = []
    for tr in rows_elems:
        row_cells: List[Cell] = []
        col_idx = 0
        for tc in tr:
            local = _local_name(tc.tag).lower()
            if local not in ("tc", "cell", "tablecell"):
                continue
            contents: List[Union[Paragraph, Table]] = []
            for c in tc:
                c_local = _local_name(c.tag).lower()
                if c_local in ("p", "paragraph"):
                    contents.append(_parse_paragraph(c, char_shapes))
                elif c_local in ("tbl", "table"):
                    nested = _parse_table(c, char_shapes)
                    if nested:
                        contents.append(nested)
            row_cells.append(Cell(contents=contents, row=len(grid), col=col_idx))
            col_idx += 1
        grid.append(row_cells)
    rows = len(grid)
    cols = max(len(r) for r in grid) if grid else 0
    return Table(rows=rows, cols=cols, cells=grid)


def _parse_body_or_sec(elem: ET.Element, char_shapes: Optional[Dict[int, CharShape]]) -> Tuple[List[Paragraph], List[Table]]:
    """body 또는 sec 한 개: 자식 p/tbl 순서대로 문단·표 리스트 생성."""
    paragraphs: List[Paragraph] = []
    tables: List[Table] = []
    for child in elem:
        local = _local_name(child.tag).lower()
        if local in ("p", "paragraph"):
            paragraphs.append(_parse_paragraph(child, char_shapes))
        elif local in ("tbl", "table"):
            t = _parse_table(child, char_shapes)
            if t:
                tables.append(t)
        elif local in ("sec", "section"):
            # 중첩 sec: 그 안 내용을 문단/표로 합침
            sub_p, sub_t = _parse_body_or_sec(child, char_shapes)
            paragraphs.extend(sub_p)
            tables.extend(sub_t)
    return paragraphs, tables


def parse_section_xml(
    section_bytes: bytes,
    char_shapes: Optional[Dict[int, CharShape]] = None,
) -> Tuple[List[Paragraph], List[Table]]:
    """
    Section XML 바이트 파싱 → (문단 리스트, 테이블 리스트).

    - root 또는 hp:body → 자식에서 p, tbl 순서대로 수집
    """
    try:
        root = ET.fromstring(section_bytes)
    except ET.ParseError:
        return [], []

    # body 찾기 (없으면 root 사용)
    body = root
    for child in root:
        if _local_name(child.tag).lower() in ("body", "content"):
            body = child
            break

    return _parse_body_or_sec(body, char_shapes)
