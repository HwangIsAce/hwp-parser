# hwp-converter

HWP(한글) 문서를 JSON / Markdown / HTML 등으로 변환하는 도구.  
[helper-hwp](https://pypi.org/project/helper-hwp/) 기반으로, **표 안의 표(중첩 표)** 와 **그림 바이너리** 추출을 확장 구현했습니다.

## 설치

```bash
uv sync
# 또는 pip install -e .
```

## 확장 기능 사용법

### 1. 중첩 표 트리 (표 안의 표)

`build_document_tree()`로 문서를 순회하면, 표 셀 안에 있는 중첩 표가 `TableNode.cells` 안에 트리 구조로 들어갑니다.

```python
from hwp_converter import build_document_tree
from hwp_converter.document_tree import TableNode, ParagraphNode

# 파일 경로 또는 이미 연 HwpDocument
nodes = build_document_tree("문서.hwp")

for node in nodes:
    if isinstance(node, ParagraphNode):
        print("문단:", node.text[:50])
    elif isinstance(node, TableNode):
        print(f"표: {node.rows}x{node.cols}, 중첩 표 수: {len(node.nested_tables)}")
        # 셀 내용 순회 (각 셀은 [ParagraphNode | TableNode, ...])
        for i, cell_contents in enumerate(node.cells):
            for item in cell_contents:
                if isinstance(item, TableNode):
                    print("  -> 표 안의 표:", item.rows, "x", item.cols)
                else:
                    print("  -> 문단:", item.text[:30])
```

### 2. 그림 바이너리 추출

`load_bin_data()`로 HWP 내 BinData를 로드하고, `get_picture_bytes()`로 PICTURE 요소에 대응하는 이미지 바이트를 가져옵니다.

```python
from helper_hwp import open_hwp
from helper_hwp.constants import ElementType
from hwp_converter import load_bin_data, get_picture_bytes

path = "문서.hwp"
bin_data = load_bin_data(path)

with open_hwp(path) as doc:
    for elem_type, elem in doc.iter_tags():
        if elem_type == ElementType.PICTURE:
            img_bytes = get_picture_bytes(path, elem, bin_data=bin_data)
            if img_bytes:
                with open("image_0.png", "wb") as f:
                    f.write(img_bytes)
```

## 프로젝트 구조

- `hwp_converter/document_tree.py` — `iter_tags()` 후처리로 중첩 표 트리 구축
- `hwp_converter/image_extract.py` — DocInfo/OLE BinData 파싱 및 그림 바이트 추출

## 의존성

- helper-hwp (HWP 5.x 파싱)
- olefile (이미지 추출 시 BinData 읽기용)
