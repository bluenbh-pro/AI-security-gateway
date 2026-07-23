# Agent 3 Professional Redesign Plan
## Policy Violation Detector (PDF-RAG 기반)

**목표**: keyword matching 대신 **법령 PDF 기반 RAG 검색**으로 위반 판정

---

## 📋 1. 현재 상태 분석

### 1.1 기존 Agent 3의 문제점
```python
# 현재 로직
if self._is_legitimate_purpose(prompt):  # "분석" 키워드만 봄
    return self._build_no_violation(data_types)  # 즉시 종료
# Step 4 (법령 적용)은 절대 실행 안 됨
```

**문제**:
- 프롬프트의 목적 키워드만으로 판단 종결
- 데이터 타입의 민감도와 무관하게 판정
- 법령 내용 자체를 검토하지 않음
- "분석" = 모든 법령 적용 제외 (잘못된 해석)

### 1.2 리소스 현황
- **법령 PDF**: 6개, 14개 파일 구성
  ```
  1_개인정보보호법/     (본법, 시행령)
  2_신용정보법/         (본법, 시행령, 시행규칙)
  3_전자금융거래법/     (본법, 시행령)
  4_정보통신망법/       (본법, 시행령, 시행규칙)
  5_데이터기본법/       (본법, 시행령, 시행규칙)
  6_AI기본법/           (본법)
  ```
- **기존 규정 JSON**: privacy_law.json (규정 스키마 참고용)

---

## 🎯 2. 새로운 아키텍처 설계

### 2.1 3단계 처리 흐름

```
┌─────────────────────────────────────────────────────┐
│ INPUT: prompt, data_types, agent2_result            │
└────────────────────┬────────────────────────────────┘
                     │
        ┌────────────▼────────────┐
        │ Phase 1: 명백한 위반    │
        │ (Explicit Violation)    │
        └────────────┬────────────┘
                     │ No violation signal?
        ┌────────────▼────────────────────────┐
        │ Phase 2: Sequential Law Checking    │
        │ (1) 개인정보보호법 관련?             │
        │ (2) 신용정보법 관련?                │
        │ (3) 전자금융거래법 관련?            │
        │ ... (나머지 법령들)                 │
        └────────────┬────────────────────────┘
                     │
        ┌────────────▼────────────────────────────┐
        │ Phase 3: RAG 검색 & 위반 판정          │
        │ - 벡터 유사도 검색 (Retrieval)          │
        │ - 리랭킹 (Ranking)                    │
        │ - 위반 가능성 판정 (Assessment)        │
        └────────────┬────────────────────────────┘
                     │
        ┌────────────▼─────────────────────┐
        │ OUTPUT: PolicyViolation           │
        │ {applicable_laws, violations, ...}│
        └──────────────────────────────────┘
```

### 2.2 모듈 구조

```python
PolicyDetectorV2/
├── _phase1_explicit_violations()
│   └─ 명백한 위반 신호 탐지 (기존 로직)
│
├── _phase2_sequential_law_checking()
│   └─ 각 법령별 순차 검토 (새로운)
│
├── _phase3_rag_search_and_assess()
│   ├─ _find_related_articles() [RAG 검색]
│   ├─ _rerank_articles() [리랭킹]
│   └─ _assess_violations() [위반 판정]
│
└── Supporting Infrastructure
    ├─ _build_laws_database() [Phase 1: 파싱청킹]
    ├─ _create_law_embeddings() [Phase 2: 색인정칭]
    └─ _embed_text() [벡터화]
```

---

## 🔧 3. 구현 단계 (6 Phase)

### Phase 1: 법령 DB 구축 (PDF 파싱)
**목표**: PDF → 구조화된 조항 데이터

**입력**: `policies/laws/*/본법.pdf`
**출력**: `laws_db.json` (또는 메모리 캐시)

```python
# 구조 예시
{
  "개인정보보호법": {
    "제3조": {
      "title": "개인정보 정의",
      "content": "개인정보란 살아있는 개인에 관한...",
      "chapter": "총칙"
    },
    "제15조": {
      "title": "개인정보 처리 원칙",
      "content": "개인정보는 목적 명시 원칙에 따라...",
      "chapter": "개인정보 처리"
    },
    ...
  },
  "신용정보법": {...},
  ...
}
```

**사용 라이브러리**:
- `pypdf` (PDF 텍스트 추출)
- `re` (조문 번호 패턴 매칭)

**검증**:
- 각 법령별 조항 개수 확인
- 샘플 조문 내용 출력 검증

---

### Phase 2: 벡터 인덱싱 (색인 정칭)
**목표**: 조항별 임베딩 벡터 생성

**입력**: `laws_db` (Phase 1 결과)
**출력**: `law_vectors` (또는 벡터 인덱스)

```python
# 구조 예시
{
  "개인정보보호법:제3조": [0.123, 0.456, ...],  # 768-dim embedding
  "개인정보보호법:제15조": [0.234, 0.567, ...],
  ...
}
```

**사용 라이브러리**:
- `sentence-transformers` (한국어 임베딩)
  - 모델: `paraphrase-multilingual-mpnet-base-v2` 또는 한국어 특화 모델
  - 또는 `OpenAI API` (embedding endpoint)

**성능 고려**:
- 임베딩 캐싱 (매번 생성하지 않음)
- 초기화 시에만 생성

---

### Phase 3: RAG 검색 (Retrieval) - 하이브리드 검색
**목표**: 프롬프트와 관련 있는 조항 찾기 (벡터 + 형태소 분석 결합)

**입력**: 
- `prompt` (요청자 프롬프트)
- `law_name` (검토할 법령)
- `law_vectors` (Phase 2 결과)

**출력**:
```python
{
  "law": "개인정보보호법",
  "related_articles": [
    {
      "article": "제15조",
      "content": "...",
      "vector_score": 0.87,
      "keyword_score": 0.95,
      "hybrid_score": 0.90,  # 0.6*vector + 0.4*keyword
      "matched_keywords": ["개인정보", "처리", "원칙"]
    },
    {
      "article": "제18조",
      "content": "...",
      "vector_score": 0.79,
      "keyword_score": 0.85,
      "hybrid_score": 0.82
    }
  ]
}
```

**알고리즘**: 하이브리드 검색 (벡터 + Nori 형태소 분석)

#### 방법 1: 벡터 기반 검색 (의미 유사도)
1. 프롬프트 벡터화
2. 각 조항과의 코사인 유사도 계산
3. vector_score: 0.0 ~ 1.0

#### 방법 2: 형태소 기반 검색 (키워드 정확도) - Nori 활용
```python
# 예시
프롬프트: "모든 직원의 급여 및 보너스 현황 분석해줄 수 있나?"
Nori 분석:
  → ["직원", "급여", "보너스", "현황", "분석"]

조문: "개인정보는 개인을 식별할 수 있는 정보로서..."
Nori 분석:
  → ["개인정보", "개인", "식별", "정보"]

매칭 키워드: ["정보"] (1/5 = 0.2)

조문: "직원 정보 관리 규칙..."
Nori 분석:
  → ["직원", "정보", "관리", "규칙"]

매칭 키워드: ["직원", "정보"] (2/5 = 0.4) → 이게 더 높음
```

#### 방법 3: 하이브리드 점수 결합
```python
hybrid_score = 0.6 * vector_score + 0.4 * keyword_score
```

**사용 라이브러리**:
- **Nori 형태소 분석**:
  - Option A: `konlpy.tag.Okt()` (간단, 빠름)
  - Option B: `kiwi` (더 정확함)
  - Option C: Elasticsearch Nori analyzer (고급)

**한국어 처리 개선**:
```
기존: "분석" 키워드만 보고 즉시 판정
      → "급여 분석" = "매출 분석" = "고객 만족도 분석" (모두 동일)

개선: Nori 형태소 분석
      → 프롬프트: [직원, 급여, 분석]
      → 조문(제18조): [개인, 동의, 제공, 금지]
      → 관련성 검사: "급여"(민감) + "금지"(제한) 
      → 높은 관련도 감지 ✓
```

---

### Phase 4: 리랭킹 (Ranking)
**목표**: 관련 조항의 순서 최적화

**입력**: Phase 3의 `related_articles` (유사도 순)

**출력**: 순서 재정렬

**전략**:
- 현재는 유사도 기반 (충분할 수 있음)
- 필요시 LLM 리랭커 추가 가능

---

### Phase 5: 위반 판정 (Assessment)
**목표**: 프롬프트가 해당 조항을 위반할 가능성 판정

**입력**: 
- `prompt`
- `article_content` (조문 내용)
- `law_name`

**출력**: 위반 여부 + 위반 사유

```python
{
  "law": "개인정보보호법",
  "article": "제18조",
  "violation_detected": True,
  "reason": "개인의 동의 없이 제3자에 제공하려는 의도 감지",
  "severity": "High"
}
```

**판정 방식**:
- **방식 A (Rule-based)**: 키워드 조합 + 패턴 매칭
- **방식 B (LLM-based)**: Claude API로 판정
- **선택**: 초기 Phase 5는 Rule-based, 필요시 LLM 추가

---

### Phase 6: 통합 & 테스트
**목표**: 전체 파이프라인 검증

**테스트 케이스**:
1. 기존 5개 케이스 (approval_5cases_full.json)
2. Block (≥76) 범위의 케이스 몇 개
3. 새로운 테스트 케이스

**검증 항목**:
- Phase 1: 각 법령별 조항 개수 정확성
- Phase 2: 벡터화 성공 여부
- Phase 3: 관련 조항 검색 성공률
- Phase 4: 리랭킹 순서 적절성
- Phase 5: 위반 판정 정확도
- Phase 6: 최종 점수 분포

---

## 📊 4. 데이터 포맷 정의

### 4.1 Laws Database Schema
```python
@dataclass
class LawArticle:
    law_name: str          # "개인정보보호법"
    article_num: str       # "제15조"
    title: str            # "개인정보 처리 원칙"
    content: str          # 조문 전체 텍스트
    chapter: Optional[str] # "개인정보 처리"
    
@dataclass
class LawsDB:
    laws: Dict[str, List[LawArticle]]  # {law_name: [articles]}
    metadata: Dict[str, Any]           # 버전, 생성일 등
```

### 4.2 Relevance Result Schema
```python
@dataclass
class RelevantArticle:
    article: LawArticle
    relevance_score: float      # 0.0 ~ 1.0
    
@dataclass
class PromptLawAnalysis:
    prompt: str
    law_name: str
    related_articles: List[RelevantArticle]
```

### 4.3 PolicyViolation Schema (기존 유지)
```python
@dataclass
class PolicyViolation:
    violation_detected: bool
    violation_type: str
    applicable_laws: List[str]  # ["개인정보보호법:제18조", ...]
    violated_sections: List[Dict]
    detected_data_types: List[str]
    explanation: str
    recommendation: str
```

---

## ⚠️ 5. 위험 관리

### 5.1 성능 이슈
- **문제**: 벡터 검색이 느릴 수 있음
- **해결**: 
  - 벡터 캐싱
  - FAISS 또는 Pinecone 사용 (필요시)
  - 배치 처리

### 5.2 정확도 이슈
- **문제**: 유사도 기반 검색이 부정확할 수 있음
- **해결**:
  - threshold 튜닝
  - 리랭킹 추가
  - LLM 판정 추가

### 5.3 법령 업데이트
- **문제**: PDF 파일이 변경되면 DB 재구축 필요
- **해결**:
  - 버전 관리
  - 자동 재구축 트리거
  - 변경 감지

---

## 🗓️ 6. 개발 일정 (예상)

| Phase | 작업 | 예상 시간 |
|-------|------|---------|
| 1 | PDF 파싱 & DB 구축 | 2-3시간 |
| 2 | 벡터 인덱싱 | 1-2시간 |
| 3 | RAG 검색 | 1-2시간 |
| 4 | 리랭킹 | 30분-1시간 |
| 5 | 위반 판정 | 1-2시간 |
| 6 | 통합 & 테스트 | 2-3시간 |
| **총계** | | **8-13시간** |

---

## 📝 7. 체크리스트

- [ ] Phase 1: laws_db.json 생성 및 검증
- [ ] Phase 2: 벡터 인덱싱 완료
- [ ] Phase 3: RAG 검색 정상 작동
- [ ] Phase 4: 리랭킹 로직 검증
- [ ] Phase 5: 위반 판정 로직 검증
- [ ] Phase 6: 기존 5개 케이스 검증
- [ ] Phase 6: Block 범위 케이스 검증
- [ ] 최종 1800 케이스 재처리
- [ ] 점수 분포 분석
- [ ] 최종 커밋

---

## 🎓 8. Professional 코드 원칙

- ✅ 명확한 타입 힌팅 (Type Hints)
- ✅ Comprehensive error handling
- ✅ Logging & Debugging
- ✅ 테스트 가능한 설계 (단위 테스트)
- ✅ 문서화 (Docstrings)
- ✅ 성능 고려 (캐싱, 배치 처리)
- ✅ 유지보수성 (명확한 네이밍, 구조)

