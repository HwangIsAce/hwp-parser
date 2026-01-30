"""
HWPX 파일 스토리지 접근 (ZIP/OCF).

- Contents/section0.xml, section1.xml, ... : 구역별 본문
- Contents/header.xml : 글자모양·문단모양 등 서식
- BinData/ : 이미지 등 바이너리
"""

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional


@dataclass
class HwpxInfo:
    """HWPX 컨테이너 기본 정보."""

    version: str = ""
    has_header: bool = False
    section_count: int = 0


class HwpxStorage:
    """
    HWPX 파일의 ZIP 스토리지 래퍼.

    - open(path): ZIP 열기
    - list_sections(): Section 인덱스 (0, 1, ...)
    - read_section(index): section{N}.xml UTF-8 바이트
    - read_header(): header.xml UTF-8 바이트 (없으면 b"")
    - read_bindata(name): BinData/... 멤버 바이트 (없으면 None)
    - list_bindata(): BinData 멤버 이름 목록
    - close()
    """

    def __init__(self, path: str | Path) -> None:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(str(path))
        self._path = path
        self._zip: Optional[zipfile.ZipFile] = None
        self._info: Optional[HwpxInfo] = None

    def open(self) -> "HwpxStorage":
        """ZIP 파일 열기 및 기본 정보 수집."""
        self._zip = zipfile.ZipFile(self._path, "r")
        self._info = _read_info(self._zip)
        return self

    def close(self) -> None:
        if self._zip is not None:
            self._zip.close()
            self._zip = None

    def __enter__(self) -> "HwpxStorage":
        return self.open()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    @property
    def info(self) -> HwpxInfo:
        if self._info is None:
            raise RuntimeError("Storage not opened; call open() first")
        return self._info

    def list_sections(self) -> Iterator[int]:
        """Section 인덱스 열거 (0, 1, ...)."""
        n = 0
        while self._zip and _section_name(n) in self._zip.namelist():
            yield n
            n += 1

    def read_section(self, index: int) -> bytes:
        """Section XML 바이트 (UTF-8)."""
        if self._zip is None:
            raise RuntimeError("Storage not opened")
        name = _section_name(index)
        if name not in self._zip.namelist():
            raise FileNotFoundError(name)
        return self._zip.read(name)

    def read_header(self) -> bytes:
        """header.xml 바이트 (UTF-8). 없으면 b\"\"."""
        if self._zip is None:
            raise RuntimeError("Storage not opened")
        name = "Contents/header.xml"
        if name not in self._zip.namelist():
            return b""
        return self._zip.read(name)

    def list_bindata(self) -> Iterator[str]:
        """BinData 멤버 이름 열거 (예: BinData/BIN0001.png)."""
        if not self._zip:
            return
        prefix = "BinData/"
        for n in self._zip.namelist():
            if n.startswith(prefix) and not n.endswith("/"):
                yield n

    def read_bindata(self, name: str) -> Optional[bytes]:
        """BinData 멤버 읽기. name은 list_bindata()에서 얻은 전체 경로."""
        if self._zip is None:
            return None
        if name not in self._zip.namelist():
            return None
        return self._zip.read(name)


def _section_name(index: int) -> str:
    return f"Contents/section{index}.xml"


def _read_info(zipf: zipfile.ZipFile) -> HwpxInfo:
    """ZIP 내부에서 section 개수·header 존재 여부 등 파악."""
    names = zipf.namelist()
    has_header = "Contents/header.xml" in names
    section_count = 0
    pattern = re.compile(r"^Contents/section(\d+)\.xml$")
    for n in names:
        m = pattern.match(n)
        if m:
            idx = int(m.group(1))
            section_count = max(section_count, idx + 1)
    version = ""
    if "version.xml" in names:
        try:
            version = zipf.read("version.xml").decode("utf-8", errors="ignore").strip()[:80]
        except Exception:
            pass
    return HwpxInfo(version=version, has_header=has_header, section_count=section_count)
