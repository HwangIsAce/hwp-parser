"""글자·문단 모양 (HWP/HWPX 공통, 참조용)."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CharShape:
    """글자 모양: 글꼴, 크기, 색, 속성."""

    font_id: int = 0
    font_size: float = 10.0
    bold: bool = False
    italic: bool = False
    underline: bool = False
    color: int = 0x000000


@dataclass
class ParaShape:
    """문단 모양: 정렬, 여백, 줄 간격 등."""

    align: str = "LEFT"  # LEFT, RIGHT, CENTER, JUSTIFY
    left_margin: int = 0
    right_margin: int = 0
    indent: int = 0
    line_spacing: int = 0
