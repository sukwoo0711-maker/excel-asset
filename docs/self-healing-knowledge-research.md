# Self-Healing Knowledge Research

작성일: 2026-06-29

## 조사 요약

기존 `auto_grill` 방식의 문제는 특정 SQLite 스키마, 특정 도메인, 특정 파일 경로가 코드에 박혀 있었다는 점이다. GitHub와 공개 사례를 보면 더 안전한 방향은 "자동 교정"이 아니라 "검출 -> 근거 수집 -> 실패 진단 -> review queue -> 사람이 승인한 수정"이다.

제한망 사내 PC에 맞는 결론은 다음과 같다.

1. 지식 수정은 자동 적용하지 않는다.
2. 검사는 config 기반으로 수행한다.
3. 원문 위치와 근거를 항상 남긴다.
4. local LLM은 판정 보조로만 사용한다.
5. 결과는 `build/` 아래에 저장하고 Git에는 넣지 않는다.

## 참고한 공개 패턴

### KnowledgeBase Guardian

GitHub의 `datarootsio/knowledgebase_guardian`은 새 문서를 기존 knowledge base와 비교해 모순 또는 부정확성을 감지하는 흐름을 제시한다. 핵심은 새 지식을 바로 받아들이지 않고, 기존 지식과의 일관성 검사를 ingest gate로 둔다는 점이다.

적용 포인트:

- 새 문서 반입 시 기존 문서와 관련 chunk 검색
- LLM 또는 규칙 기반 judge로 contradiction 후보 생성
- 모순 가능성이 있으면 반입을 막고 review finding 생성

출처: https://github.com/datarootsio/knowledgebase_guardian

### SelfHealingRAG 계열

Self-healing RAG 구현들은 대체로 다음 루프를 둔다.

```text
retrieve -> answer -> evaluate -> diagnose failure -> retry with adjusted retrieval or prompt
```

여기서 중요한 점은 원본 지식을 자동으로 고치는 것이 아니라, 검색 실패나 답변 실패를 진단하고 다음 retrieval/prompt를 조정한다는 것이다. 문서 자체를 수정하는 경우에는 별도 승인 단계가 필요하다.

조사 키워드:

- `SelfHealingRAG`
- `self healing RAG`
- `RAG failure diagnosis`
- `RAG evaluation loop`

### RAG 평가 프레임워크

RAGAS, DeepEval, Tonic Validate 같은 평가 도구들은 faithfulness, answer relevance, context precision 같은 지표를 통해 답변과 컨텍스트의 품질을 측정한다. self-healing knowledge에 바로 가져올 수 있는 부분은 "정답을 믿기 전에 평가 결과를 남긴다"는 운영 방식이다.

적용 포인트:

- contradiction finding을 단순 문자열 매칭으로 끝내지 않기
- finding마다 evidence, confidence, source span을 기록
- 기준 미달 시 open query로 보류

대표 프로젝트:

- https://github.com/explodinggradients/ragas
- https://github.com/confident-ai/deepeval
- https://github.com/TonicAI/tonic_validate

### Knowledge Graph + RAG

Knowledge graph 기반 RAG 프로젝트들은 문서 단락을 그대로 비교하기보다 entity, relation, claim 단위로 나누는 방식을 쓴다. 사내 문서의 규칙 충돌을 보려면 "문장 전체"보다 "대상, 조건, 행위, 제약" 구조로 쪼개는 것이 더 좋다.

적용 포인트:

- claim schema: `subject`, `condition`, `action`, `modality`, `source`
- 같은 subject/action에서 modality가 충돌하는지 확인
- 조건이 다르면 contradiction이 아니라 condition boundary로 분류

## 개선 설계

### 1. Ingest Gate

새 문서나 수정 문서가 들어오면 다음을 수행한다.

```text
changed files
-> claim extraction
-> related claim retrieval
-> contradiction/duplicate/condition-boundary classification
-> findings.json
-> human review
```

### 2. Claim Extraction

초기 버전은 규칙 기반으로 충분하다.

대상:

- `must`, `shall`, `required`, `forbidden`, `never`
- `필수`, `금지`, `반드시`, `해야`, `하지 말`
- 번호 목록, bullet rule

고도화:

- local LLM으로 claim을 JSON schema로 추출
- Presidio 등으로 PII 마스킹 후 평가
- 원문 file/line/source hash 유지

### 3. Retrieval

전체 문서를 전부 LLM에 넣지 않는다.

추천:

- 변경 claim 기준 keyword/BM25 후보 검색
- 필요하면 embedding rerank
- top-k만 judge에 전달

### 4. Judge

판정 타입:

- `conflict`
- `possible_conflict`
- `duplicate`
- `condition_boundary`
- `consistent`
- `needs_review`

local LLM을 쓰더라도 최종 수정은 사람이 한다.

### 5. Open Query

finding은 다음 구조로 저장한다.

```json
{
  "verdict": "possible_conflict",
  "severity": "medium",
  "claim_a": {"file": "docs/a.md", "line": 12},
  "claim_b": {"file": "docs/b.md", "line": 30},
  "reason": "Related claims use opposite requirement polarity.",
  "recommendation": "Ask owner which rule has priority."
}
```

## 이 repo에 반영한 내용

- `auto_grill.py`를 하드코딩 없는 중립 consistency checker로 교체
- `self_heal.py`를 repo 내부 scan wrapper로 축소
- 자동 수정 제거
- findings를 `build/self_heal/findings.json`에 저장
- 특정 제품, 게임, 영상, 개인 실험 데이터 제거
- `.gitignore`에 생성물과 민감 가능 산출물 추가

## 다음 고도화 제안

1. `claims.jsonl` 캐시를 만들고 변경 파일만 incremental scan.
2. SQLite/Markdown export 전에 PII masking hook 추가.
3. finding에 source hash를 추가해 stale finding을 자동 폐기.
4. PR template 또는 사내 변경 요청 양식과 연결.
5. local LLM judge 결과를 사람이 확인한 라벨 데이터로 평가.
