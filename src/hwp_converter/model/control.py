"""제어 요소 (그림, 수식 등) — HWP/HWPX 공통."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Control:
    """제어 요소 베이스."""

    control_id: Optional[str] = None
    data: Optional[bytes] = None


@dataclass
class Picture(Control):
    """그림: BinData 인덱스 또는 바이트."""

    bin_index: Optional[int] = None
    image_bytes: Optional[bytes] = None


@dataclass
class Equation(Control):
    """수식 (메타만)."""

    pass
