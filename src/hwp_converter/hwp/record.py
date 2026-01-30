"""
HWP 레코드 스트림 읽기.

- 4바이트 헤더: tag_id(10) | level(10) | size(12); size==0xFFF이면 다음 4바이트가 실제 크기
- payload: size 바이트
"""

import struct
from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO, Iterator, Optional

from .constants import RecordBitMask


@dataclass
class Record:
    """HWP 레코드 (tag_id, level, size, data)."""

    tag_id: int
    level: int
    size: int
    data: bytes

    @classmethod
    def read_from_stream(cls, stream: BinaryIO) -> Optional["Record"]:
        """스트림에서 레코드 하나 읽기. 끝이면 None."""
        header_bytes = stream.read(4)
        if len(header_bytes) < 4:
            return None

        header = struct.unpack("<I", header_bytes)[0]
        tag_id = header & RecordBitMask.TAG_ID_MASK
        level = (header >> RecordBitMask.LEVEL_SHIFT) & RecordBitMask.LEVEL_MASK
        size = (header >> RecordBitMask.SIZE_SHIFT) & RecordBitMask.SIZE_MASK

        if size == RecordBitMask.SIZE_EXTENDED:
            ext = stream.read(4)
            if len(ext) < 4:
                return None
            size = struct.unpack("<I", ext)[0]

        data = stream.read(size)
        if len(data) < size:
            raise ValueError(
                f"Unexpected end of stream (expected {size} bytes, got {len(data)})"
            )
        return cls(tag_id=tag_id, level=level, size=size, data=data)


def iter_records(data: bytes) -> Iterator[Record]:
    """바이트 스트림에서 레코드를 순차적으로 yield."""
    stream = BytesIO(data)
    while True:
        rec = Record.read_from_stream(stream)
        if rec is None:
            break
        yield rec
