"""
HWP 파서: 스토리지 → 공통 문서 모델(Document).

- DocInfo 파싱 → CharShape 맵
- Section 스트림 파싱 → Section(paragraphs, tables)
- Document(sections, version, compressed, encrypted)
- Picture 컨트롤 시 BinData에서 image_bytes 채우기
"""

from pathlib import Path
from typing import List, Union

from ..model.control import Picture
from ..model.document import Document, Section
from ..storage import HwpOleStorage
from .doc_info import parse_char_shapes
from .section import parse_section


def _fill_picture_bytes(doc: Document, storage: HwpOleStorage) -> None:
    """Document 내 Picture 컨트롤에 storage.read_bindata(bin_index)로 image_bytes 채우기."""
    for sec in doc.sections:
        for p in sec.paragraphs:
            for r in p.runs:
                if not isinstance(r.control, Picture) or r.control.bin_index is None:
                    continue
                data = storage.read_bindata(r.control.bin_index)
                if data is not None:
                    r.control = Picture(
                        bin_index=r.control.bin_index,
                        image_bytes=data,
                        data=r.control.data,
                        control_id=r.control.control_id,
                    )
        for t in sec.tables:
            for row in t.cells:
                for cell in row:
                    for c in cell.contents:
                        if hasattr(c, "runs"):
                            for r in c.runs:
                                if not isinstance(r.control, Picture) or r.control.bin_index is None:
                                    continue
                                data = storage.read_bindata(r.control.bin_index)
                                if data is not None:
                                    r.control = Picture(
                                        bin_index=r.control.bin_index,
                                        image_bytes=data,
                                        data=r.control.data,
                                        control_id=r.control.control_id,
                                    )


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

        doc = Document(
            sections=sections,
            version=version,
            compressed=compressed,
            encrypted=encrypted,
        )
        _fill_picture_bytes(doc, storage)
        return doc
    finally:
        if own_storage:
            storage.close()
