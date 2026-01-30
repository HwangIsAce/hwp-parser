"""문단·런 모델 (HWP/HWPX 공통)."""

from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

from .shape import CharShape

if TYPE_CHECKING:
    from .control import Control


@dataclass
class Run:
    """런: 동일 글자 모양이 적용된 텍스트 단위 또는 인라인 제어(그림/수식)."""

    text: str = ""
    char_shape_id: Optional[int] = None  # header.xml / DocInfo 참조용
    char_shape: Optional[CharShape] = None  # 해석된 글자 모양 (선택)
    control: Optional["Control"] = None  # 인라인 제어 (Picture, Equation 등)


@dataclass
class Paragraph:
    """문단: 런 리스트 + 문단 모양 참조."""

    runs: List[Run] = field(default_factory=list)
    para_shape_id: Optional[int] = None
    page_break: bool = False

    @property
    def text(self) -> str:
        return "".join(r.text for r in self.runs)
