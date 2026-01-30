"""
DocInfo 스트림 파싱.

- HWPTAG_CHAR_SHAPE → char_shape_id → CharShape (model)
- 필요 시 HWPTAG_PARA_SHAPE, HWPTAG_FACE_NAME 등 확장
"""

import struct
from typing import Dict

from ..model.shape import CharShape
from .constants import RecordTag
from .record import iter_records


def parse_char_shapes(docinfo_data: bytes) -> Dict[int, CharShape]:
    """
    DocInfo 바이트에서 HWPTAG_CHAR_SHAPE 레코드만 파싱하여
    char_shape_id -> CharShape 매핑 반환.
    """
    result: Dict[int, CharShape] = {}
    char_shape_id = 0

    for rec in iter_records(docinfo_data):
        if rec.tag_id != RecordTag.HWPTAG_CHAR_SHAPE:
            continue
        try:
            if len(rec.data) < 56:
                result[char_shape_id] = CharShape()
                char_shape_id += 1
                continue
            # 기준 크기 (offset 42, INT32, 포인트 * 100)
            base_size = struct.unpack("<i", rec.data[42:46])[0]
            font_size = base_size / 100.0 if base_size > 0 else 10.0
            # 속성 (offset 46, UINT32)
            attr = struct.unpack("<I", rec.data[46:50])[0]
            bold = (attr & 0x1) != 0
            italic = (attr & 0x2) != 0
            underline = (attr & 0x4) != 0
            font_id = struct.unpack("<H", rec.data[0:2])[0]
            color = (
                struct.unpack("<I", rec.data[52:56])[0]
                if len(rec.data) >= 56
                else 0
            )
            result[char_shape_id] = CharShape(
                font_id=font_id,
                font_size=font_size,
                bold=bold,
                italic=italic,
                underline=underline,
                color=color,
            )
        except (struct.error, IndexError):
            result[char_shape_id] = CharShape()
        char_shape_id += 1

    return result
