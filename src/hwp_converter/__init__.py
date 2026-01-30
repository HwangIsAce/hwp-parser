"""
hwp-converter: HWP/HWPX 문서를 JSON/Markdown/HTML 등으로 변환

계층: storage → hwp|hwpx → model → api
"""

from .api import (
    document_to_dict,
    document_to_json,
    document_to_markdown,
    document_to_text,
    load,
    load_hwp,
    load_hwpx,
    to_json,
    to_markdown,
    to_text,
)

__version__ = "0.1.0"
__all__ = [
    "load",
    "load_hwp",
    "load_hwpx",
    "document_to_text",
    "document_to_markdown",
    "document_to_dict",
    "document_to_json",
    "to_text",
    "to_markdown",
    "to_json",
]
