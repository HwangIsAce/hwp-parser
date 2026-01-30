"""HWP 전용 파싱 (레코드, DocInfo, Section, 컨트롤)."""

from .parser import parse_hwp
from .record import Record, iter_records

__all__ = [
    "parse_hwp",
    "Record",
    "iter_records",
]
