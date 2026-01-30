# hwp-converter

HWP / HWPX 문서를 JSON, Markdown, 평문 텍스트로 변환하는 도구.  
외부 한글 엔진 없이 스토리지·레코드/XML 파서를 직접 구현했으며, 문단·표(중첩 표)·그림·수식을 공통 모델로 다룹니다.

## 설치

```bash
uv sync
# 또는 pip install -e .
```

## 사용 방법

```python
from hwp_converter import load, to_text, to_markdown, to_json

# 파일 경로만 넣으면 .hwp / .hwpx 자동 감지
doc   = load("문서.hwp")
text  = to_text("문서.hwpx")
md    = to_markdown("문서.hwp")
json_ = to_json("문서.hwp", indent=2)

# Document 객체로 변환만 할 때
doc = load("문서.hwpx")
from hwp_converter import document_to_text, document_to_markdown, document_to_json
document_to_text(doc)
document_to_markdown(doc)
document_to_json(doc, indent=2)
```

포맷 지정 로드: `load_hwp(path)`, `load_hwpx(path)`.

## 예시

**원본 (캡쳐본)**  

![공고문 원본 (평가방법, 표 안의 표)](docs/example/공고문_원본.png)

**파싱 후** (`to_markdown(파일경로)` — 같은 구간):

```markdown
### 3

### 평가방법

### □ 평가방법 : 서면평가 (30%) + 대국민 온라인 평가 (70%) 점수를 합산하여 고득점자 순으로 시상자 결정*

* 최종점수 동점자는 서면평가 심사항목인 ①실현 가능성 및 지속 가능성, ②주제 적합성, ③공모 내용 혁신성, ④공익·공동체성 순으로 해당지표 득점이 높은 자로 순위 결정

< 최종점수 산출방법 >

| 구분 | 비중 | 산출방법 |
| --- | --- | --- |
| 서면평가 | 30% | 1차 평가점수 30점으로 환산 |
| 대국민 온라인 평가 | 70% |  |

| 순위 | 1위 | 2위 | 3위 | 4위 | 5위 | 6위 |
| --- | --- | --- | --- | --- | --- | --- |
| 점수 | 70점 | 65점 | 60 | 55 | 50 | 45 |

* 분야별 순위에 따른 차등 점수 부여
```

바깥 표(구분/비중/산출방법)와 그 셀 안에 있던 안쪽 표(순위·점수)가 각각 마크다운 테이블로 나옵니다.
