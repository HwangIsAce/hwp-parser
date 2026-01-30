"""표·셀 모델 (HWP/HWPX 공통, 중첩 표 지원)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Union

from .paragraph import Paragraph


# 셀 내용: 문단 리스트 또는 중첩 표
CellContent = Union[Paragraph, "Table"]


@dataclass
class Cell:
    """셀: 문단 리스트 또는 중첩 표."""

    contents: List[CellContent] = field(default_factory=list)
    row: int = 0
    col: int = 0
    rowspan: int = 1
    colspan: int = 1

    @property
    def text(self) -> str:
        parts = []
        for c in self.contents:
            if isinstance(c, Paragraph):
                parts.append(c.text)
            elif isinstance(c, Table):
                parts.append(f"[표 {c.rows}x{c.cols}]")
        return "\n".join(parts)


@dataclass
class Table:
    """표: 행/열 + 셀 그리드 (중첩 표 포함)."""

    rows: int = 0
    cols: int = 0
    cells: List[List[Cell]] = field(default_factory=list)

    @property
    def nested_tables(self) -> List["Table"]:
        result: List[Table] = []
        for row in self.cells:
            for cell in row:
                for c in cell.contents:
                    if isinstance(c, Table):
                        result.append(c)
        return result
