"""
HWP 5.0 레코드·제어 상수.

한글문서파일형식_5.0_revision1.3 참고.
"""

from enum import IntEnum


class RecordTag(IntEnum):
    """레코드 태그 ID (10비트)."""

    # DocInfo (0x10~0x1B)
    HWPTAG_DOCUMENT_PROPERTIES = 0x10
    HWPTAG_ID_MAPPINGS = 0x11
    HWPTAG_BIN_DATA = 0x12
    HWPTAG_FACE_NAME = 0x13
    HWPTAG_BORDER_FILL = 0x14
    HWPTAG_CHAR_SHAPE = 0x15
    HWPTAG_TAB_DEF = 0x16
    HWPTAG_NUMBERING = 0x17
    HWPTAG_BULLET = 0x18
    HWPTAG_PARA_SHAPE = 0x19
    HWPTAG_STYLE = 0x1A
    HWPTAG_DOC_DATA = 0x1B

    # BodyText (실제: 0x42~)
    HWPTAG_PARA_HEADER = 0x42
    HWPTAG_PARA_TEXT = 0x43
    HWPTAG_PARA_CHAR_SHAPE = 0x44
    HWPTAG_PARA_LINE_SEG = 0x45
    HWPTAG_PARA_RANGE_TAG = 0x46
    HWPTAG_CTRL_HEADER = 0x47
    HWPTAG_LIST_HEADER = 0x48
    HWPTAG_PAGE_DEF = 0x49
    HWPTAG_FOOTNOTE_SHAPE = 0x4A
    HWPTAG_PAGE_BORDER_FILL = 0x4B
    HWPTAG_SHAPE_COMPONENT = 0x4C
    HWPTAG_TABLE = 0x4D
    HWPTAG_SHAPE_COMPONENT_PICTURE = 0x4E
    HWPTAG_SHAPE_COMPONENT_OLE = 0x50
    HWPTAG_EQEDIT = 0x51
    HWPTAG_CTRL_DATA = 0x52


class RecordBitMask(IntEnum):
    """레코드 헤더 비트 마스크 (4바이트)."""

    TAG_ID_MASK = 0x3FF
    LEVEL_MASK = 0x3FF
    SIZE_MASK = 0xFFF
    SIZE_EXTENDED = 0xFFF
    LEVEL_SHIFT = 10
    SIZE_SHIFT = 20


class CharConstants(IntEnum):
    """문자·제어 데이터 크기."""

    CONTROL_BOUNDARY = 31
    CONTROL_DATA_SIZE = 12
    CODE_SIZE = 2


class ExtendedControlCode(IntEnum):
    """확장 제어 코드 (2바이트)."""

    TABLE = 1
    PICTURE = 2
    OLE = 3
    EQUATION = 11
    FOOTNOTE = 14
    ENDNOTE = 15
    HYPERLINK = 16
    COMMENT = 21
    SHAPE = 22
    SHAPE_COMPONENT = 23


class CharControlCode(IntEnum):
    """제어 문자 코드 (2바이트)."""

    LINE_BREAK = 10
    PARA_BREAK = 13
    HYPHEN = 24
    KEEP_WORD_SPACE = 30
    FIXED_WIDTH_SPACE = 31


class InlineControlCode(IntEnum):
    """인라인 제어 코드."""

    TAB = 9
    PAGE_NUMBER = 19


class PageBreakType(IntEnum):
    """문단 페이지 구분 타입."""

    NORMAL = 0
    COLUMN_BREAK = 1
    PAGE_BREAK = 2
    SECTION_BREAK = 3


class ControlID(IntEnum):
    """컨트롤 ID (control_data 첫 4바이트, 리틀엔디언)."""

    TABLE = 0x74626C20  # 'tbl '
    AUTO_NUMBER = 0x61746E6F
    PAGE_NUM_POS = 0x70676E70
    HEADER = 0x64616568
    FOOTER = 0x746F6F66


class ParagraphConstants(IntEnum):
    """문단 레코드 오프셋."""

    MIN_HEADER_SIZE = 8
    PAGE_BREAK_TYPE_OFFSET = 7
    CONTROL_ID_SIZE = 4
