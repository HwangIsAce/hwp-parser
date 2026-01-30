"""
Section(본문) 스트림 파싱.

- 레코드 그룹화: PARA_HEADER 기준 문단, CTRL_HEADER TABLE + HWPTAG_TABLE/LIST_HEADER 등으로 표 메타
- 문단 → model.Paragraph (runs, page_break)
- 표 메타 + 셀 문단 → model.Table (cells)
"""

import io
import struct
from typing import Dict, List, Optional, Tuple

from ..model.paragraph import Paragraph, Run
from ..model.shape import CharShape
from ..model.table import Cell, Table
from .char_reader import Char
from .constants import (
    ControlID,
    PageBreakType,
    ParagraphConstants,
    RecordTag,
)
from .record import Record, iter_records


def _chars_to_runs(
    chars: List[Char],
    char_shape_ids: List[Tuple[int, int]],
    char_shapes: Optional[Dict[int, CharShape]] = None,
) -> List[Run]:
    """문자 리스트와 (위치, shape_id) 리스트로 Run 리스트 생성."""
    def shape_at(pos: int) -> Optional[int]:
        sid = None
        for p, s in char_shape_ids:
            if p <= pos:
                sid = s
            else:
                break
        return sid

    runs: List[Run] = []
    i = 0
    while i < len(chars):
        pos = i
        sid = shape_at(pos)
        text_parts: List[str] = []
        while i < len(chars):
            if shape_at(i) != sid:
                break
            text_parts.append(chars[i].to_str())
            i += 1
        text = "".join(text_parts)
        if text or sid is not None:
            run = Run(text=text, char_shape_id=sid)
            if char_shapes and sid is not None:
                run.char_shape = char_shapes.get(sid)
            runs.append(run)
    return runs


def _paragraph_from_records(
    records: List[Record],
    char_shapes: Optional[Dict[int, CharShape]] = None,
) -> Paragraph:
    """문단 레코드 그룹 → model.Paragraph."""
    page_break_type = 0
    char_shape_ids: List[Tuple[int, int]] = []
    chars: List[Char] = []

    for rec in records:
        if rec.tag_id == RecordTag.HWPTAG_PARA_HEADER:
            if len(rec.data) >= ParagraphConstants.MIN_HEADER_SIZE:
                page_break_type = rec.data[ParagraphConstants.PAGE_BREAK_TYPE_OFFSET]
        elif rec.tag_id == RecordTag.HWPTAG_PARA_CHAR_SHAPE:
            data_len = len(rec.data)
            for offset in range(0, data_len, 8):
                if offset + 8 <= data_len:
                    pos = struct.unpack("<I", rec.data[offset : offset + 4])[0]
                    shape_id = struct.unpack("<I", rec.data[offset + 4 : offset + 8])[0]
                    char_shape_ids.append((pos, shape_id))
        elif rec.tag_id == RecordTag.HWPTAG_PARA_TEXT:
            stream = io.BytesIO(rec.data)
            while True:
                c = Char.read_from_stream(stream)
                if c is None:
                    break
                chars.append(c)

    runs = _chars_to_runs(chars, char_shape_ids, char_shapes)
    return Paragraph(
        runs=runs,
        para_shape_id=None,
        page_break=(page_break_type == PageBreakType.PAGE_BREAK),
    )


def _parse_table_metadata(records: List[Record]) -> List[dict]:
    """Section 레코드 전체를 한 번 순회하며 테이블 메타데이터만 추출."""
    table_list: List[dict] = []
    current_idx: Optional[int] = None

    for rec in records:
        if rec.tag_id == RecordTag.HWPTAG_CTRL_HEADER and len(rec.data) >= 4:
            ctrl_id = struct.unpack("<I", rec.data[0:4])[0]
            if ctrl_id == ControlID.TABLE:
                table_list.append({
                    "ctrl_id": ctrl_id,
                    "cell_para_counts": [],
                    "rows": 0,
                    "cols": 0,
                    "cell_spacing": 0,
                    "row_sizes": None,
                    "cell_widths": [],
                    "cell_heights": [],
                    "cell_colspans": [],
                    "cell_rowspans": [],
                })
                current_idx = len(table_list) - 1
            else:
                current_idx = None
            continue

        if current_idx is None:
            continue

        t = table_list[current_idx]

        if rec.tag_id == RecordTag.HWPTAG_SHAPE_COMPONENT and len(rec.data) >= 36:
            if "x" not in t:
                y = struct.unpack("<i", rec.data[8:12])[0]
                x = struct.unpack("<i", rec.data[12:16])[0]
                width = struct.unpack("<I", rec.data[16:20])[0]
                height = struct.unpack("<I", rec.data[20:24])[0]
                margins = struct.unpack("<hhhh", rec.data[28:36])
                t["x"] = x
                t["y"] = y
                t["width"] = width
                t["height"] = height
                t["margin_left"] = margins[0]
                t["margin_right"] = margins[1]
                t["margin_top"] = margins[2]
                t["margin_bottom"] = margins[3]

        elif rec.tag_id == RecordTag.HWPTAG_LIST_HEADER and len(rec.data) >= 2:
            para_count = struct.unpack("<H", rec.data[0:2])[0]
            t["cell_para_counts"].append(para_count)
            cell_attr_offset = 7
            if len(rec.data) >= cell_attr_offset + 26:
                col = struct.unpack("<H", rec.data[cell_attr_offset + 1 : cell_attr_offset + 3])[0]
                row = struct.unpack("<H", rec.data[cell_attr_offset + 3 : cell_attr_offset + 5])[0]
                colspan = struct.unpack("<H", rec.data[cell_attr_offset + 5 : cell_attr_offset + 7])[0]
                rowspan = struct.unpack("<H", rec.data[cell_attr_offset + 7 : cell_attr_offset + 9])[0]
                w = struct.unpack("<I", rec.data[cell_attr_offset + 9 : cell_attr_offset + 13])[0]
                h = struct.unpack("<I", rec.data[cell_attr_offset + 13 : cell_attr_offset + 17])[0]
                t.setdefault("cell_widths", []).append(w)
                t.setdefault("cell_heights", []).append(h)
                t.setdefault("cell_colspans", []).append(colspan)
                t.setdefault("cell_rowspans", []).append(rowspan)

        elif rec.tag_id == RecordTag.HWPTAG_TABLE and len(rec.data) >= 8:
            rows = struct.unpack("<H", rec.data[4:6])[0]
            cols = struct.unpack("<H", rec.data[6:8])[0]
            cell_spacing = struct.unpack("<h", rec.data[8:10])[0]
            t["rows"] = rows
            t["cols"] = cols
            t["cell_spacing"] = cell_spacing
            row_size_offset = 18
            if rows > 0 and len(rec.data) >= row_size_offset + (2 * rows):
                row_sizes = []
                for i in range(rows):
                    off = row_size_offset + (i * 2)
                    row_sizes.append(struct.unpack("<H", rec.data[off : off + 2])[0])
                t["row_sizes"] = row_sizes

    return table_list


def _distribute_cell_paragraphs(
    rows: int,
    cols: int,
    cell_para_counts: List[int],
    cell_colspans: Optional[List[int]] = None,
    cell_rowspans: Optional[List[int]] = None,
    paragraphs: Optional[List[Paragraph]] = None,
) -> List[List[Cell]]:
    """셀별 문단 개수와 colspan/rowspan으로 셀 그리드 생성. paragraphs가 있으면 해당 문단으로 채움."""
    if rows <= 0 or cols <= 0:
        return []
    covered: set = set()
    cell_index = 0
    para_index = 0
    grid: List[List[Optional[Cell]]] = [[None] * cols for _ in range(rows)]
    colspans = cell_colspans or [1] * len(cell_para_counts)
    rowspans = cell_rowspans or [1] * len(cell_para_counts)

    for r in range(rows):
        for c in range(cols):
            if (r, c) in covered:
                continue
            if cell_index >= len(cell_para_counts):
                break
            n = cell_para_counts[cell_index]
            colspan = colspans[cell_index] if cell_index < len(colspans) else 1
            rowspan = rowspans[cell_index] if cell_index < len(rowspans) else 1
            for rr in range(r, r + rowspan):
                for cc in range(c, c + colspan):
                    covered.add((rr, cc))
            contents: List[Paragraph] = []
            if paragraphs is not None:
                for _ in range(n):
                    if para_index < len(paragraphs):
                        contents.append(paragraphs[para_index])
                        para_index += 1
            cell = Cell(
                contents=contents,
                row=r,
                col=c,
                rowspan=rowspan,
                colspan=colspan,
            )
            for rr in range(r, r + rowspan):
                for cc in range(c, c + colspan):
                    grid[rr][cc] = cell
            cell_index += 1

    # 남은 칸(파싱 부족 시)은 빈 셀로
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] is None:
                grid[r][c] = Cell(contents=[], row=r, col=c, rowspan=1, colspan=1)
    return [[grid[r][c] for c in range(cols)] for r in range(rows)]


def parse_section(
    section_data: bytes,
    char_shapes: Optional[Dict[int, CharShape]] = None,
) -> Tuple[List[Paragraph], List[Table]]:
    """
    Section 바이트 파싱 → (standalone 문단 리스트, 테이블 리스트).

    - 문단은 문서 출현 순서; 테이블 셀 내 문단은 Table.cells 안에만 포함.
    """
    all_records = list(iter_records(section_data))
    table_meta_list = _parse_table_metadata(all_records)

    # 1) 문단 순서대로 생성 + 테이블별 "셀 문단 시작 인덱스" 기록
    all_paras_ordered: List[Paragraph] = []
    current_para_records: List[Record] = []
    table_para_start: List[int] = []
    para_index = 0

    for rec in all_records:
        if rec.tag_id == RecordTag.HWPTAG_CTRL_HEADER and len(rec.data) >= 4:
            ctrl_id = struct.unpack("<I", rec.data[0:4])[0]
            if ctrl_id == ControlID.TABLE:
                table_para_start.append(para_index)
        if rec.tag_id == RecordTag.HWPTAG_PARA_HEADER:
            if current_para_records:
                all_paras_ordered.append(
                    _paragraph_from_records(current_para_records, char_shapes)
                )
                para_index += 1
            current_para_records = [rec]
        else:
            current_para_records.append(rec)
    if current_para_records:
        all_paras_ordered.append(
            _paragraph_from_records(current_para_records, char_shapes)
        )
        para_index += 1

    # 2) 테이블별 셀 문단 구간 [start, start+n) 로 standalone / 테이블 셀 분리
    standalone: List[Paragraph] = []
    tables: List[Table] = []
    consumed = 0
    for t_idx, tmeta in enumerate(table_meta_list):
        start = (
            table_para_start[t_idx]
            if t_idx < len(table_para_start)
            else len(all_paras_ordered)
        )
        n_need = sum(tmeta.get("cell_para_counts", []))
        while consumed < start and consumed < len(all_paras_ordered):
            standalone.append(all_paras_ordered[consumed])
            consumed += 1
        cell_paras = all_paras_ordered[consumed : consumed + n_need]
        consumed += n_need
        rows = tmeta.get("rows", 0)
        cols = tmeta.get("cols", 0)
        cell_para_counts = tmeta.get("cell_para_counts", [])
        cells_grid = _distribute_cell_paragraphs(
            rows,
            cols,
            cell_para_counts,
            tmeta.get("cell_colspans"),
            tmeta.get("cell_rowspans"),
            cell_paras,
        )
        tables.append(Table(rows=rows, cols=cols, cells=cells_grid))

    while consumed < len(all_paras_ordered):
        standalone.append(all_paras_ordered[consumed])
        consumed += 1

    return standalone, tables
