"""API 레이어 테스트: load, to_text, to_markdown, to_json, document_to_*."""

from pathlib import Path

import pytest

from hwp_converter import (
    document_to_text,
    document_to_markdown,
    document_to_json,
    load,
    load_hwpx,
    to_text,
    to_markdown,
    to_json,
)
from hwp_converter.model.document import Document, Section
from hwp_converter.model.paragraph import Paragraph, Run
from hwp_converter.model.table import Cell, Table


def test_document_to_text(minimal_document: Document) -> None:
    text = document_to_text(minimal_document)
    assert "안녕하세요" in text


def test_document_to_text_with_table(document_with_table: Document) -> None:
    text = document_to_text(document_with_table)
    assert "표 위 문단" in text
    assert "셀 내용" in text


def test_document_to_markdown(minimal_document: Document) -> None:
    md = document_to_markdown(minimal_document)
    assert "안녕하세요" in md


def test_document_to_json(minimal_document: Document) -> None:
    s = document_to_json(minimal_document, indent=2)
    assert "sections" in s
    assert "안녕하세요" in s


def test_to_text_with_document(minimal_document: Document) -> None:
    assert "안녕하세요" in to_text(minimal_document)


def test_to_markdown_with_document(minimal_document: Document) -> None:
    assert "안녕하세요" in to_markdown(minimal_document)


def test_to_json_with_document(minimal_document: Document) -> None:
    out = to_json(minimal_document, indent=None)
    assert "sections" in out


def test_load_returns_same_document(minimal_document: Document) -> None:
    assert load(minimal_document) is minimal_document


# 샘플 HWPX 파일이 있으면 로드·변환 검증 (없으면 skip)
SAMPLE_HWPX = Path(__file__).resolve().parent.parent / "docs" / "input" / "제3차_개인위생_점검표.hwpx"


@pytest.mark.skipif(not SAMPLE_HWPX.exists(), reason="샘플 HWPX 파일 없음")
def test_load_hwpx_sample() -> None:
    doc = load_hwpx(SAMPLE_HWPX)
    assert len(doc.sections) >= 1
    # 문단 또는 표가 하나 이상 있으면 성공
    total = sum(len(s.paragraphs) + len(s.tables) for s in doc.sections)
    assert total >= 1


@pytest.mark.skipif(not SAMPLE_HWPX.exists(), reason="샘플 HWPX 파일 없음")
def test_load_auto_detects_hwpx() -> None:
    doc = load(SAMPLE_HWPX)
    assert len(doc.sections) >= 1


@pytest.mark.skipif(not SAMPLE_HWPX.exists(), reason="샘플 HWPX 파일 없음")
def test_to_text_from_hwpx_path() -> None:
    text = to_text(SAMPLE_HWPX)
    assert isinstance(text, str)
    assert len(text) >= 0


@pytest.mark.skipif(not SAMPLE_HWPX.exists(), reason="샘플 HWPX 파일 없음")
def test_to_markdown_from_hwpx_path() -> None:
    md = to_markdown(SAMPLE_HWPX)
    assert isinstance(md, str)


@pytest.mark.skipif(not SAMPLE_HWPX.exists(), reason="샘플 HWPX 파일 없음")
def test_to_json_from_hwpx_path() -> None:
    js = to_json(SAMPLE_HWPX, indent=2)
    assert "sections" in js
