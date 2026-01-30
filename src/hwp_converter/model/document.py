"""문서·구역 모델 (HWP/HWPX 공통)."""

from dataclasses import dataclass, field
from typing import List

from .paragraph import Paragraph
from .table import Table


@dataclass
class Section:
    """구역: 문단·표·그림 등의 순서된 리스트."""

    paragraphs: List[Paragraph] = field(default_factory=list)
    tables: List[Table] = field(default_factory=list)
    # controls: List[Control] (Picture, Equation 등) — 필요 시 추가


@dataclass
class Document:
    """문서: 메타 + 구역 리스트."""

    sections: List[Section] = field(default_factory=list)
    # 메타 (선택)
    version: str = ""
    compressed: bool = False
    encrypted: bool = False
