"""테스트 픽스처: 최소 Document 및 샘플 파일 경로."""

import pytest

from hwp_converter.model.document import Document, Section
from hwp_converter.model.paragraph import Paragraph, Run
from hwp_converter.model.table import Cell, Table


@pytest.fixture
def minimal_document() -> Document:
    """문단 하나만 있는 최소 Document."""
    run = Run(text="안녕하세요.")
    para = Paragraph(runs=[run])
    sec = Section(paragraphs=[para], tables=[])
    return Document(sections=[sec], version="5.0", compressed=True)


@pytest.fixture
def document_with_table() -> Document:
    """문단 + 표가 있는 Document."""
    p1 = Paragraph(runs=[Run(text="표 위 문단")])
    cell = Cell(contents=[Paragraph(runs=[Run(text="셀 내용")])], row=0, col=0)
    tbl = Table(rows=1, cols=1, cells=[[cell]])
    sec = Section(paragraphs=[p1], tables=[tbl])
    return Document(sections=[sec])
