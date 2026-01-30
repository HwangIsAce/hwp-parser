"""
문단 내 문자(Char) 읽기.

- 2바이트 코드; 코드 <= 31이면 제어문자(인라인/확장 제어는 추가 12+2바이트)
"""

import struct
from dataclasses import dataclass
from typing import BinaryIO, Optional

from .constants import (
    CharConstants,
    CharControlCode,
    ExtendedControlCode,
)


@dataclass
class Char:
    """문단 내 한 문자 (일반/제어/인라인/확장)."""

    code: int
    is_control: bool  # 제어 문자 (줄바꿈 등)
    is_extended: bool  # 확장 제어 (표, 그림 등)
    control_data: Optional[bytes] = None

    @classmethod
    def read_from_stream(cls, stream: BinaryIO) -> Optional["Char"]:
        """스트림에서 문자 하나 읽기. 끝이면 None."""
        code_bytes = stream.read(2)
        if len(code_bytes) < 2:
            return None
        code = struct.unpack("<H", code_bytes)[0]

        if code > CharConstants.CONTROL_BOUNDARY:
            return cls(code=code, is_control=False, is_extended=False)

        # 제어 문자 (단독 2바이트)
        if code in (
            CharControlCode.LINE_BREAK,
            CharControlCode.PARA_BREAK,
            CharControlCode.HYPHEN,
            CharControlCode.KEEP_WORD_SPACE,
            CharControlCode.FIXED_WIDTH_SPACE,
        ):
            return cls(code=code, is_control=True, is_extended=False)

        # 인라인/확장 제어: 추가 12바이트 + 2바이트 반복
        control_data = stream.read(CharConstants.CONTROL_DATA_SIZE)
        code_repeat = stream.read(2)
        if len(control_data) < CharConstants.CONTROL_DATA_SIZE or len(code_repeat) < 2:
            return cls(code=code, is_control=True, is_extended=False)
        code_repeat = struct.unpack("<H", code_repeat)[0]
        if code != code_repeat:
            return cls(code=code, is_control=True, is_extended=False)

        extended = code in (
            ExtendedControlCode.TABLE,
            ExtendedControlCode.PICTURE,
            ExtendedControlCode.OLE,
            ExtendedControlCode.EQUATION,
            ExtendedControlCode.FOOTNOTE,
            ExtendedControlCode.ENDNOTE,
            ExtendedControlCode.HYPERLINK,
            ExtendedControlCode.COMMENT,
            ExtendedControlCode.SHAPE,
            ExtendedControlCode.SHAPE_COMPONENT,
        )
        return cls(
            code=code,
            is_control=True,
            is_extended=extended,
            control_data=control_data,
        )

    def to_str(self) -> str:
        """문자열로 변환 (일반 문자·줄바꿈·공백만)."""
        if not self.is_control and not self.is_extended:
            try:
                return chr(self.code)
            except (ValueError, OverflowError):
                return ""
        if self.is_control and not self.is_extended:
            if self.code == CharControlCode.LINE_BREAK:
                return "\n"
            if self.code == CharControlCode.PARA_BREAK:
                return "\n"
            if self.code in (
                CharControlCode.KEEP_WORD_SPACE,
                CharControlCode.FIXED_WIDTH_SPACE,
            ):
                return " "
        return ""
