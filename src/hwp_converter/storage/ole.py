"""
HWP 파일 스토리지 접근 (CFB/OLE).

- FileHeader: 서명·버전·압축 여부
- DocInfo: 문서 공통 정보 (zlib 압축 해제)
- BodyText/Section{N}: 본문 스트림 (zlib 압축 해제)
- BinData: 바이너리 데이터 스트림 목록 (선택)
"""

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

try:
    import olefile
except ImportError:
    olefile = None  # type: ignore

# HWP FileHeader 상수 (한컴 스펙)
FILE_HEADER_SIZE = 256
SIGNATURE_SIZE = 32
SIGNATURE = b"HWP Document File"
VERSION_OFFSET = 0x20
FLAGS_OFFSET = 0x24
FLAG_COMPRESSED = 0x01
FLAG_ENCRYPTED = 0x02
FLAG_DISTRIBUTED = 0x04  # 배포용 문서 → ViewText 사용


@dataclass
class FileHeader:
    """HWP FileHeader (256바이트)."""

    signature: bytes
    version: bytes  # 4 bytes, e.g. 5.1.0.1
    flags: int  # DWORD
    compressed: bool = False
    encrypted: bool = False
    distributed: bool = False

    @property
    def version_str(self) -> str:
        """버전 문자열 (e.g. '5.1.0.1')."""
        if len(self.version) < 4:
            return ""
        return ".".join(str(b) for b in self.version[:4])

    @property
    def body_prefix(self) -> str:
        """본문 스트림 접두사: 'BodyText' 또는 'ViewText'."""
        return "ViewText" if self.distributed else "BodyText"


def _decompress(data: bytes) -> bytes:
    """zlib 압축 해제 (HWP: -zlib.MAX_WBITS)."""
    try:
        return zlib.decompress(data, -zlib.MAX_WBITS)
    except zlib.error:
        return data


def _parse_header(raw: bytes) -> FileHeader:
    """FileHeader 256바이트 파싱."""
    if len(raw) < FLAGS_OFFSET + 4:
        raise ValueError("FileHeader too short")
    signature = raw[:SIGNATURE_SIZE]
    version = raw[VERSION_OFFSET : VERSION_OFFSET + 4]
    flags = struct.unpack("<I", raw[FLAGS_OFFSET : FLAGS_OFFSET + 4])[0]
    return FileHeader(
        signature=signature,
        version=version,
        flags=flags,
        compressed=(flags & FLAG_COMPRESSED) != 0,
        encrypted=(flags & FLAG_ENCRYPTED) != 0,
        distributed=(flags & FLAG_DISTRIBUTED) != 0,
    )


class HwpOleStorage:
    """
    HWP 파일의 OLE 스토리지 래퍼.

    - open(path): 파일 열기
    - header: FileHeader
    - read_doc_info(): DocInfo 바이트 (압축 해제됨)
    - read_section(n): Section n 바이트 (압축 해제됨)
    - list_sections(): Section 인덱스 열거
    - read_bindata(index): BinData 스트림 (선택)
    - close()
    """

    def __init__(self, path: str | Path) -> None:
        if olefile is None:
            raise ImportError("olefile is required. pip install olefile")
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(str(path))
        self._path = path
        self._ole: Optional[olefile.OleFileIO] = None
        self._header: Optional[FileHeader] = None

    def open(self) -> "HwpOleStorage":
        """OLE 파일 열기 및 FileHeader 읽기."""
        with open(self._path, "rb") as f:
            data = f.read()
        self._ole = olefile.OleFileIO(data)
        if not self._ole.exists("FileHeader"):
            raise ValueError("Not an HWP file: FileHeader not found")
        raw = self._ole.openstream("FileHeader").read()
        if len(raw) < FILE_HEADER_SIZE:
            raise ValueError("FileHeader too short")
        self._header = _parse_header(raw[:FILE_HEADER_SIZE])
        if not raw[:SIGNATURE_SIZE].startswith(SIGNATURE):
            raise ValueError("Invalid HWP signature")
        return self

    def close(self) -> None:
        """스트림 닫기."""
        if self._ole is not None:
            self._ole.close()
            self._ole = None

    def __enter__(self) -> "HwpOleStorage":
        return self.open()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    @property
    def header(self) -> FileHeader:
        if self._header is None:
            raise RuntimeError("Storage not opened; call open() first")
        return self._header

    def read_doc_info(self) -> bytes:
        """DocInfo 스트림 읽기 (압축 시 해제)."""
        if self._ole is None:
            raise RuntimeError("Storage not opened")
        if not self._ole.exists("DocInfo"):
            return b""
        data = self._ole.openstream("DocInfo").read()
        if self.header.compressed:
            data = _decompress(data)
        return data

    def list_sections(self) -> Iterator[int]:
        """Section 인덱스 열거 (0, 1, ...)."""
        prefix = self.header.body_prefix
        n = 0
        while self._ole and self._ole.exists(f"{prefix}/Section{n}"):
            yield n
            n += 1

    def list_bindata(self) -> Iterator[int]:
        """BinData 스트림 인덱스 열거 (BinaryData0, BinaryData1, ...)."""
        n = 0
        while self._ole and self._ole.exists(f"BinData/BinaryData{n}"):
            yield n
            n += 1

    def read_section(self, index: int) -> bytes:
        """Section 스트림 읽기 (압축 시 해제)."""
        if self._ole is None:
            raise RuntimeError("Storage not opened")
        path = f"{self.header.body_prefix}/Section{index}"
        if not self._ole.exists(path):
            raise FileNotFoundError(path)
        data = self._ole.openstream(path).read()
        if self.header.compressed:
            data = _decompress(data)
        return data

    def read_bindata(self, index: int) -> Optional[bytes]:
        """BinData 스트림 읽기 (BinaryData0, BinaryData1, ...)."""
        if self._ole is None:
            return None
        name = f"BinData/BinaryData{index}"
        try:
            if not self._ole.exists(name):
                return None
            data = self._ole.openstream(name).read()
            if self.header.compressed and len(data) > 0:
                try:
                    data = _decompress(data)
                except zlib.error:
                    pass
            return data
        except Exception:
            return None
