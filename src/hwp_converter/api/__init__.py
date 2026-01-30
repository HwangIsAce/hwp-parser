"""
Public API: HWP 로드 및 Document → 텍스트/마크다운/JSON 변환.

- load_hwp(path_or_storage) → Document
- document_to_text(doc), document_to_markdown(doc), document_to_json(doc)
- to_text(path), to_markdown(path), to_json(path) — 경로만 넣고 한 번에 변환
"""

from pathlib import Path
from typing import Union

from ..model.document import Document
from ..storage import HwpOleStorage
from .convert import (
    document_to_dict,
    document_to_json,
    document_to_markdown,
    document_to_text,
)


def load_hwp(path_or_storage: Union[str, Path, HwpOleStorage]) -> Document:
    """
    HWP 파일 또는 열린 스토리지에서 Document(공통 모델) 로드.

    - path_or_storage: 파일 경로(str/Path) 또는 이미 open()된 HwpOleStorage
    """
    from ..hwp import parse_hwp
    return parse_hwp(path_or_storage)


def to_text(path_or_document: Union[str, Path, Document]) -> str:
    """경로 또는 Document를 받아 평문 텍스트로 반환."""
    if isinstance(path_or_document, Document):
        return document_to_text(path_or_document)
    doc = load_hwp(Path(path_or_document))
    return document_to_text(doc)


def to_markdown(path_or_document: Union[str, Path, Document]) -> str:
    """경로 또는 Document를 받아 마크다운 문자열로 반환."""
    if isinstance(path_or_document, Document):
        return document_to_markdown(path_or_document)
    doc = load_hwp(Path(path_or_document))
    return document_to_markdown(doc)


def to_json(
    path_or_document: Union[str, Path, Document],
    indent: Union[None, int] = 2,
) -> str:
    """경로 또는 Document를 받아 JSON 문자열로 반환."""
    if isinstance(path_or_document, Document):
        return document_to_json(path_or_document, indent=indent)
    doc = load_hwp(Path(path_or_document))
    return document_to_json(doc, indent=indent)


__all__ = [
    "load_hwp",
    "document_to_text",
    "document_to_markdown",
    "document_to_dict",
    "document_to_json",
    "to_text",
    "to_markdown",
    "to_json",
]
