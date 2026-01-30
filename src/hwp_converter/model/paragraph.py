"""문단·런 모델 (HWP/HWPX 공통)."""

from dataclasses import dataclass, field
from typing import List, Optional

from .shape import CharShape


@dataclass
class Run:
    """런: 동일 글자 모양이 적용된 텍스트 단위."""

    text: str = ""
    char_shape_id: Optional[int] = None  # header.xml / DocInfo 참조용
    char_shape: Optional[CharShape] = None  # 해석된 글자 모양 (선택)


@dataclass
class Paragraph:
    """문단: 런 리스트 + 문단 모양 참조."""

    runs: List[Run] = field(default_factory=list)
    para_shape_id: Optional[int] = None
    page_break: bool = False

    @property
    def text(self) -> str:
        return "".join(r.text for r in self.runs)
