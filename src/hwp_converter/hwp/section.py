"""
Section(본문) 스트림 파싱.

- 레코드 그룹화: PARA_HEADER 기준 문단, CTRL_HEADER TABLE + HWPTAG_TABLE/LIST_HEADER 등으로 표 메타
- 문단 → model.Paragraph (runs, page_break)
- 표 메타 + 셀 문단 → model.Table (cells)
"""

import io
import struct
from typing import Dict, Iterator, List, Optional, Tuple, Union

from ..model.control import Equation, Picture
from ..model.paragraph import Paragraph, Run
from ..model.shape import CharShape
from ..model.table import Cell, Table
from .char_reader import Char
from .constants import (
    ControlID,
    ExtendedControlCode,
    PageBreakType,
    ParagraphConstants,
    RecordTag,
)
from .record import Record, iter_records

# 셀 내용: 문단 또는 중첩 표
CellContent = Union[Paragraph, Table]

# HWPTAG_SHAPE_COMPONENT_PICTURE: 개체 공통(46) + 개체 요소(26) + 그림 개체 속성(그림 정보 5바이트 at offset 68)
# 그림 정보(표 32): 5바이트, 바이트 3-4 = UINT16 BinItem ID
_PICTURE_BIN_ID_OFFSET = 46 + 26 + 68 + 3  # 143, bytes [143:145]


def _extract_picture_bin_indices(records: List[Record]) -> List[Optional[int]]:
    """Section 레코드에서 HWPTAG_SHAPE_COMPONENT_PICTURE 순서대로 BinData ID 추출."""
    result: List[Optional[int]] = []
    for rec in records:
        if rec.tag_id != RecordTag.HWPTAG_SHAPE_COMPONENT_PICTURE:
            continue
        if len(rec.data) < _PICTURE_BIN_ID_OFFSET + 2:
            result.append(None)
            continue
        try:
            bin_id = struct.unpack(
                "<H", rec.data[_PICTURE_BIN_ID_OFFSET : _PICTURE_BIN_ID_OFFSET + 2]
            )[0]
            result.append(bin_id)
        except (struct.error, IndexError):
            result.append(None)
    return result


def _chars_to_runs(
    chars: List[Char],
    char_shape_ids: List[Tuple[int, int]],
    char_shapes: Optional[Dict[int, CharShape]] = None,
    picture_bin_iter: Optional[Iterator[Optional[int]]] = None,
) -> List[Run]:
    """문자 리스트와 (위치, shape_id) 리스트로 Run 리스트 생성. 그림/수식 확장 제어 시 Control Run 생성."""
    def shape_at(pos: int) -> Optional[int]:
        sid = None
        for p, s in char_shape_ids:
            if p <= pos:
                sid = s
            else:
                break
        return sid

    def next_bin() -> Optional[int]:
        if picture_bin_iter is None:
            return None
        try:
            return next(picture_bin_iter)
        except StopIteration:
            return None

    runs: List[Run] = []
    i = 0
    while i < len(chars):
        ch = chars[i]
        # 확장 제어: 그림 → Picture Run, 수식 → Equation Run
        if ch.is_extended and ch.code == ExtendedControlCode.PICTURE:
            bin_index = next_bin()
            runs.append(Run(text="", control=Picture(bin_index=bin_index, data=ch.control_data)))
            i += 1
            continue
        if ch.is_extended and ch.code == ExtendedControlCode.EQUATION:
            runs.append(Run(text="", control=Equation(data=ch.control_data)))
            i += 1
            continue
        # 일반/제어 문자: shape 기준으로 묶어서 Run
        pos = i
        sid = shape_at(pos)
        text_parts: List[str] = []
        while i < len(chars):
            c = chars[i]
            if c.is_extended and c.code in (ExtendedControlCode.PICTURE, ExtendedControlCode.EQUATION):
                break
            if shape_at(i) != sid:
                break
            text_parts.append(c.to_str())
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
    picture_bin_iter: Optional[Iterator[Optional[int]]] = None,
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

    runs = _chars_to_runs(chars, char_shape_ids, char_shapes, picture_bin_iter)
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


def _next_item_start(records: List[Record], start: int) -> Optional[int]:
    """start 다음에 나오는 첫 PARA_HEADER 또는 CTRL_HEADER TABLE 인덱스."""
    for i in range(start + 1, len(records)):
        rec = records[i]
        if rec.tag_id == RecordTag.HWPTAG_PARA_HEADER:
            return i
        if rec.tag_id == RecordTag.HWPTAG_CTRL_HEADER and len(rec.data) >= 4:
            ctrl_id = struct.unpack("<I", rec.data[0:4])[0]
            if ctrl_id == ControlID.TABLE:
                return i
    return None


def _skip_table_meta(records: List[Record], idx: int) -> int:
    """CTRL_HEADER TABLE(idx) 다음 테이블 메타 레코드를 건너뛰고, 셀 본문 시작 인덱스 반환."""
    i = idx + 1
    while i < len(records) and records[i].tag_id != RecordTag.HWPTAG_TABLE:
        i += 1
    return i + 1 if i < len(records) else i


def _distribute_cell_contents(
    rows: int,
    cols: int,
    cell_para_counts: List[int],
    cell_colspans: Optional[List[int]] = None,
    cell_rowspans: Optional[List[int]] = None,
    contents: Optional[List[CellContent]] = None,
) -> List[List[Cell]]:
    """셀별 문단/표 개수와 colspan/rowspan으로 셀 그리드 생성. contents에 문단·중첩표 혼합 가능."""
    if rows <= 0 or cols <= 0:
        return []
    covered: set = set()
    cell_index = 0
    content_index = 0
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
            cell_contents: List[CellContent] = []
            if contents is not None:
                for _ in range(n):
                    if content_index < len(contents):
                        cell_contents.append(contents[content_index])
                        content_index += 1
            cell = Cell(
                contents=cell_contents,
                row=r,
                col=c,
                rowspan=rowspan,
                colspan=colspan,
            )
            for rr in range(r, r + rowspan):
                for cc in range(c, c + colspan):
                    grid[rr][cc] = cell
            cell_index += 1

    for r in range(rows):
        for c in range(cols):
            if grid[r][c] is None:
                grid[r][c] = Cell(contents=[], row=r, col=c, rowspan=1, colspan=1)
    return [[grid[r][c] for c in range(cols)] for r in range(rows)]


def _distribute_cell_paragraphs(
    rows: int,
    cols: int,
    cell_para_counts: List[int],
    cell_colspans: Optional[List[int]] = None,
    cell_rowspans: Optional[List[int]] = None,
    paragraphs: Optional[List[Paragraph]] = None,
) -> List[List[Cell]]:
    """셀별 문단 개수와 colspan/rowspan으로 셀 그리드 생성. paragraphs가 있으면 해당 문단으로 채움."""
    contents: Optional[List[CellContent]] = list(paragraphs) if paragraphs else None
    return _distribute_cell_contents(
        rows, cols, cell_para_counts, cell_colspans, cell_rowspans, contents
    )


def _parse_one_item(
    records: List[Record],
    idx: int,
    table_meta_index_ref: List[int],
    table_meta_list: List[dict],
    char_shapes: Optional[Dict[int, CharShape]],
    picture_bin_iter: Iterator[Optional[int]],
) -> Tuple[CellContent, int]:
    """
    레코드 스트림에서 문단 또는 표 하나 파싱 (재귀: 표 셀에 중첩표 포함).
    반환: (Paragraph | Table, 다음 아이템 시작 인덱스).
    """
    if idx >= len(records):
        return (Paragraph(), idx)

    rec = records[idx]
    # 문단: PARA_HEADER로 시작하는 블록
    if rec.tag_id == RecordTag.HWPTAG_PARA_HEADER:
        end = _next_item_start(records, idx)
        end_idx = end if end is not None else len(records)
        para_records = records[idx:end_idx]
        para = _paragraph_from_records(para_records, char_shapes, picture_bin_iter)
        return (para, end_idx)

    # 표: CTRL_HEADER TABLE + 메타 스킵 후 셀 개수만큼 아이템 재귀 파싱
    if rec.tag_id == RecordTag.HWPTAG_CTRL_HEADER and len(rec.data) >= 4:
        ctrl_id = struct.unpack("<I", rec.data[0:4])[0]
        if ctrl_id == ControlID.TABLE:
            ti = table_meta_index_ref[0]
            table_meta_index_ref[0] += 1
            if ti >= len(table_meta_list):
                return (Paragraph(), idx + 1)
            tmeta = table_meta_list[ti]
            body_start = _skip_table_meta(records, idx)
            rows = tmeta.get("rows", 0)
            cols = tmeta.get("cols", 0)
            cell_para_counts = tmeta.get("cell_para_counts", [])
            n_total = sum(cell_para_counts)
            cell_contents: List[CellContent] = []
            cur = body_start
            for _ in range(n_total):
                if cur >= len(records):
                    break
                item, cur = _parse_one_item(
                    records, cur, table_meta_index_ref, table_meta_list,
                    char_shapes, picture_bin_iter,
                )
                cell_contents.append(item)
            cells_grid = _distribute_cell_contents(
                rows,
                cols,
                cell_para_counts,
                tmeta.get("cell_colspans"),
                tmeta.get("cell_rowspans"),
                cell_contents,
            )
            return (Table(rows=rows, cols=cols, cells=cells_grid), cur)

    # 그 외: 다음 아이템 시작까지 스킵 후 다음부터 파싱
    next_start = _next_item_start(records, idx)
    if next_start is not None:
        return _parse_one_item(
            records, next_start, table_meta_index_ref, table_meta_list,
            char_shapes, picture_bin_iter,
        )
    return (Paragraph(), len(records))


def _find_first_item_start(records: List[Record]) -> Optional[int]:
    """첫 PARA_HEADER 또는 CTRL_HEADER TABLE 인덱스."""
    for i in range(len(records)):
        rec = records[i]
        if rec.tag_id == RecordTag.HWPTAG_PARA_HEADER:
            return i
        if rec.tag_id == RecordTag.HWPTAG_CTRL_HEADER and len(rec.data) >= 4:
            ctrl_id = struct.unpack("<I", rec.data[0:4])[0]
            if ctrl_id == ControlID.TABLE:
                return i
    return None


def parse_section(
    section_data: bytes,
    char_shapes: Optional[Dict[int, CharShape]] = None,
) -> Tuple[List[Paragraph], List[Table]]:
    """
    Section 바이트 파싱 → (standalone 문단 리스트, 테이블 리스트).

    - 문단·표를 출현 순서대로 파싱; 표 셀 안에 문단·중첩표를 재귀적으로 채움.
    """
    all_records = list(iter_records(section_data))
    table_meta_list = _parse_table_metadata(all_records)
    picture_bin_indices = _extract_picture_bin_indices(all_records)
    picture_bin_iter: Iterator[Optional[int]] = iter(picture_bin_indices)
    table_meta_index_ref: List[int] = [0]

    content_blocks: List[CellContent] = []
    idx = _find_first_item_start(all_records)
    while idx is not None and idx < len(all_records):
        item, next_idx = _parse_one_item(
            all_records,
            idx,
            table_meta_index_ref,
            table_meta_list,
            char_shapes,
            picture_bin_iter,
        )
        content_blocks.append(item)
        idx = next_idx if next_idx > idx else None
        if idx is not None and idx >= len(all_records):
            break

    standalone: List[Paragraph] = [b for b in content_blocks if isinstance(b, Paragraph)]
    tables: List[Table] = [b for b in content_blocks if isinstance(b, Table)]
    return standalone, tables
