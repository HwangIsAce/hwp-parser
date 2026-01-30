"""
Public API: HWP/HWPX 로드 및 Document → 텍스트/마크다운/JSON 변환.

- load(path): 확장자로 HWP/HWPX 자동 분기 → Document
- load_hwp(path_or_storage), load_hwpx(path_or_storage) → Document
- document_to_text(doc), document_to_markdown(doc), document_to_json(doc)
- to_text(path), to_markdown(path), to_json(path) — 경로만 넣고 한 번에 변환 (.hwp/.hwpx 모두)
"""

from pathlib import Path
from typing import Union

from ..model.document import Document
from ..storage import HwpOleStorage, HwpxStorage
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


def load_hwpx(path_or_storage: Union[str, Path, HwpxStorage]) -> Document:
    """
    HWPX 파일 또는 열린 스토리지에서 Document(공통 모델) 로드.

    - path_or_storage: 파일 경로(str/Path) 또는 이미 open()된 HwpxStorage
    """
    from ..hwpx import parse_hwpx
    return parse_hwpx(path_or_storage)


def load(path_or_document: Union[str, Path, Document]) -> Document:
    """
    경로 또는 Document를 받아 Document 반환.

    - Document면 그대로 반환.
    - .hwp → load_hwp, .hwpx → load_hwpx (확장자 소문자 기준).
    """
    if isinstance(path_or_document, Document):
        return path_or_document
    path = Path(path_or_document)
    suffix = path.suffix.lower()
    if suffix == ".hwpx":
        return load_hwpx(path)
    if suffix == ".hwp":
        return load_hwp(path)
    # 기본값: HWP로 시도 (기존 동작)
    return load_hwp(path)


def to_text(path_or_document: Union[str, Path, Document]) -> str:
    """경로 또는 Document를 받아 평문 텍스트로 반환 (.hwp/.hwpx 자동)."""
    if isinstance(path_or_document, Document):
        return document_to_text(path_or_document)
    doc = load(Path(path_or_document))
    return document_to_text(doc)


def to_markdown(path_or_document: Union[str, Path, Document]) -> str:
    """경로 또는 Document를 받아 마크다운 문자열로 반환 (.hwp/.hwpx 자동)."""
    if isinstance(path_or_document, Document):
        return document_to_markdown(path_or_document)
    doc = load(Path(path_or_document))
    return document_to_markdown(doc)


def to_json(
    path_or_document: Union[str, Path, Document],
    indent: Union[None, int] = 2,
) -> str:
    """경로 또는 Document를 받아 JSON 문자열로 반환 (.hwp/.hwpx 자동)."""
    if isinstance(path_or_document, Document):
        return document_to_json(path_or_document, indent=indent)
    doc = load(Path(path_or_document))
    return document_to_json(doc, indent=indent)


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
