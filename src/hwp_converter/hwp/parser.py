"""
HWP 파서: 스토리지 → 공통 문서 모델(Document).

- DocInfo 파싱 → CharShape 맵
- Section 스트림 파싱 → Section(paragraphs, tables)
- Document(sections, version, compressed, encrypted)
"""

from pathlib import Path
from typing import List, Union

from ..model.document import Document, Section
from ..storage import HwpOleStorage
from .doc_info import parse_char_shapes
from .section import parse_section


def parse_hwp(
    path_or_storage: Union[str, Path, HwpOleStorage],
) -> Document:
    """
    HWP 파일 또는 열린 스토리지에서 Document(공통 모델) 생성.

    - path_or_storage: 파일 경로(str/Path) 또는 이미 open()된 HwpOleStorage
    - 스토리지를 넘기면 호출자가 close() 책임.
    """
    own_storage = False
    if isinstance(path_or_storage, (str, Path)):
        storage = HwpOleStorage(Path(path_or_storage))
        storage.open()
        own_storage = True
    else:
        storage = path_or_storage

    try:
        version = storage.header.version_str
        compressed = storage.header.compressed
        encrypted = storage.header.encrypted

        docinfo_bytes = storage.read_doc_info()
        char_shapes = parse_char_shapes(docinfo_bytes)

        sections: List[Section] = []
        for idx in storage.list_sections():
            section_bytes = storage.read_section(idx)
            paragraphs, tables = parse_section(section_bytes, char_shapes)
            sections.append(Section(paragraphs=paragraphs, tables=tables))

        return Document(
            sections=sections,
            version=version,
            compressed=compressed,
            encrypted=encrypted,
        )
    finally:
        if own_storage:
            storage.close()
