"""
HWPX 파서: ZIP/XML 스토리지 → 공통 문서 모델(Document).

- Contents/header.xml → CharShape 맵 (선택)
- Contents/section{N}.xml → Section(paragraphs, tables)
- Document(sections, version, ...)
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..model.document import Document, Section
from ..model.paragraph import Paragraph, Run
from ..model.shape import CharShape
from ..model.table import Cell, Table
from ..storage import HwpxStorage
from .section import parse_section_xml


def _local_name(tag: str) -> str:
    """XML 태그 로컬 이름 (네임스페이스 제거)."""
    return tag.split("}")[-1] if "}" in tag else tag


def _parse_char_shapes_from_header(header_xml: bytes) -> Dict[int, CharShape]:
    """header.xml에서 글자모양 매핑 추출 (있으면). OWPML/HWPX 스키마에 맞게 확장 가능."""
    result: Dict[int, CharShape] = {}
    try:
        root = ET.fromstring(header_xml)
    except ET.ParseError:
        return result
    for i, elem in enumerate(root.iter()):
        local = _local_name(elem.tag).lower()
        if local in ("charshape", "charpr"):
            result[len(result)] = CharShape()
    return result


def parse_hwpx(
    path_or_storage: Union[str, Path, HwpxStorage],
) -> Document:
    """
    HWPX 파일 또는 열린 스토리지에서 Document(공통 모델) 생성.

    - path_or_storage: 파일 경로(str/Path) 또는 이미 open()된 HwpxStorage
    """
    own_storage = False
    if isinstance(path_or_storage, (str, Path)):
        storage = HwpxStorage(Path(path_or_storage))
        storage.open()
        own_storage = True
    else:
        storage = path_or_storage

    try:
        version = storage.info.version or ""
        header_bytes = storage.read_header()
        char_shapes = _parse_char_shapes_from_header(header_bytes) if header_bytes else {}

        sections: List[Section] = []
        for idx in storage.list_sections():
            section_bytes = storage.read_section(idx)
            paragraphs, tables = parse_section_xml(section_bytes, char_shapes)
            sections.append(Section(paragraphs=paragraphs, tables=tables))

        return Document(
            sections=sections,
            version=version,
            compressed=False,
            encrypted=False,
        )
    finally:
        if own_storage:
            storage.close()
