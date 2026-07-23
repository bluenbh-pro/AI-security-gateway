# Agent 점수 산출 공식 및 로직

**문서 작성일**: 2026-07-23  
**목적**: 각 Agent의 점수 계산 방식 일원화 및 투명성 확보

---

## 📊 Agent 1: 데이터 민감도 분류 (A1)

### 점수 계산 공식

```
A1_SCORE = MAX(severity_mapping.values())
```

**설명**: 감지된 모든 데이터 등급 중 **가장 높은 심각도**를 최종 점수로 사용

### 데이터 등급별 심각도

| 등급 | 심각도 | 설명 |
|------|--------|------|
| **고유식별정보** | 95 | 법령 4가지 (주민번호, 여권, 운전면허, 외국인등록증) |
| **극비** | 90 | 회사 생존 위협 (사업전략, M&A, 기술코드) |
| **민감정보** | 80 | 사생활 침해 (건강, 종교, 정치, 범죄경력) |
| **신용정보** | 70 | 금융거래 영향 (신용도, 거래내역, 계좌) |
| **개인정보** | 70 | 개인 식별 가능 (이름, 주소, 전화) |
| **대외비** | 60 | 경영 영향 (미공개 경영정보, 미발표 정책) |
| **일반정보** | 30 | 공개된 정보 (뉴스, 보도자료) |

### 의사결정 매핑

```python
if 0 <= a1_score <= 30:
    a1_decision = "Allow"
elif 31 <= a1_score <= 50:
    a1_decision = "Conditional"
elif 51 <= a1_score <= 80:
    a1_decision = "Approval"
else:  # 81-100
    a1_decision = "Block"
```

### 예시

**프롬프트**: "모든 고객의 개인정보와 신용정보를 엑셀로 다운로드할 수 있나요?"

```
감지된 데이터 등급: [개인정보(70), 신용정보(70)]
severity_mapping: {"개인정보": 70, "신용정보": 70}
A1_SCORE = max(70, 70) = 70 → "Approval"
```

---

## 📊 Agent 2: 컨텍스트 위험도 (A2)

### 점수 계산 공식

```
A2_SCORE = purpose_risk × 0.6
         + dept_appropriateness × 0.4
         + (100 - role_credibility) × 0.1
         + min(semantic_attack_boost, 50)

범위: 0-100 (cap at 100)
```

### 세부 계산 단계

#### Step 1: Purpose Risk (의도 위험도, 가중치 0.6)
```
purpose_risk = A1_SCORE × intent_multiplier × 0.6

multiplier:
- SAFE: 1.0   (데이터 무관)
- READ: 1.1   (데이터 조회)
- CREATE: 1.5 (분석/가공/산출)
- EXTRACT: 2.0 (데이터 반출)
```

#### Step 2: Department Appropriateness (부서 적절성, 가중치 0.4)
```
dept_appropriateness = LLM이 프롬프트 분석 → 부서 권한 평가 (0-100)
최종값: dept_appropriateness × 0.4
```

#### Step 3: Role Credibility (역할 신뢰도, 가중치 0.1)
```
직급별 신뢰도 (0-100, 높을수록 신뢰도 높음):
- 임원: 100 (최고 신뢰도)
- 파트장: 85 (높은 신뢰도)
- 프로: 70 (중간 신뢰도)
- 외주인력: 20 (낮은 신뢰도)

페널티: (100 - role_credibility) × 0.1
```

#### Step 4: Semantic Attack Boost (의미론적 공격 신호, 최대 50점)
```
공격 패턴 감지 시 0-50점 추가
(각 공격당 10-15점, min(score, 50))
```

### 의사결정 매핑

```python
if 0 <= a2_score <= 30:
    a2_decision = "Allow"
elif 31 <= a2_score <= 50:
    a2_decision = "Conditional"
elif 51 <= a2_score <= 80:
    a2_decision = "Approval"
else:  # 81-100
    a2_decision = "Block"
```

### 예시

**조건**: 영업팀(프로) + "모든 고객정보 다운로드"

```
Step 1: purpose_risk = 70 × 2.0 (EXTRACT) × 0.6 = 84
Step 2: dept_appropriateness = LLM(50) × 0.4 = 20
Step 3: role_credibility = 70 (프로) → 페널티 = (100-70) × 0.1 = 3
Step 4: semantic_attack_boost = 25 (대량 추출) → cap 50 = 25

A2_SCORE = 84 + 20 + 3 + 25
         = 132 → cap 100 → "Block"
```

---

## 📊 Agent 3: 정책 위반 감지 (A3)

### 점수 계산 공식

```
Phase 1: JSON 정확 매칭 (신뢰도 > 0.8)
Phase 2: TF-IDF + Cosine 유사도 벡터 검색
Phase 3: LLM 검증 (신뢰도 < 0.8일 때)

A3_SCORE = matched_regulation.severity
```

**설명**: `data/regulations/all_regulations.json`에서 매칭된 규정의 severity 값을 그대로 사용

### 의사결정 매핑

```python
if 0 <= a3_score <= 30:
    a3_decision = "Allow"
elif 31 <= a3_score <= 50:
    a3_decision = "Conditional"
elif 51 <= a3_score <= 80:
    a3_decision = "Approval"
else:  # 81-100
    a3_decision = "Block"
```

### 계산 특징

- **Phase 1**: 키워드 정확 매칭 (가장 빠름)
- **Phase 2**: 의미론적 검색 (팀원 아이디어, TF-IDF 활용)
- **Phase 3**: LLM 검증 (거짓 긍정 제거, 신뢰도 강화)

### 예시

**프롬프트**: "신용정보를 외부에 판매할 수 있나?"

```
Phase 1/2/3: 신용정보법 위반 매칭
matched_regulation.severity = 85
A3_SCORE = 85 → "Approval"
```

---

## 📊 Agent 5: 공격 탐지 (A5)

### 점수 계산 공식 (OWASP 기준)

```
Step 1: base_severity = OWASP 카테고리별 기본값
Step 2: multiplier = 금융 데이터 가중치 × 공격 문맥 가중치
Step 3: adjusted_score = base_severity × multiplier
Step 4: keyword_boost = min(keyword_count × 2, 10)
Step 5: final_score = confidence_curve(adjusted_score + keyword_boost, confidence)

범위: 0-100
```

### 공격 카테고리별 Base Severity

#### CRITICAL (85-100) - 즉시 차단
- **SQL Injection**: 95점
  - 데이터베이스 쿼리 조작
  
- **System Exploitation**: 95점
  - 시스템 명령어 직접 실행
  
- **Prompt Injection**: 95점
  - AI 지시사항 변조/우회

#### HIGH (65-84) - 승인 필요
- **Unauthorized Data Access**: 80점
  - 권한 없는 데이터 대량 추출
  
- **Financial Crime**: 80점
  - 거래 기록 위조/변조
  
- **Data Exfiltration**: 80점
  - 민감 정보 외부 유출

#### MEDIUM/LOW (35-64)
- **Privilege Escalation**: 70점
- **Identity Spoofing**: 65점

### 신뢰도 곡선 적용

```python
def confidence_curve(base_score, confidence):
    confidence = max(0.0, min(confidence, 1.0))  # 0-1 범위
    
    if confidence < 0.5:
        # 신뢰도 낮음: 점수 50% 감소
        return base_score * 0.5
    elif confidence < 0.8:
        # 신뢰도 중간: 선형 보간 (50% → 100%)
        factor = 0.5 + (confidence - 0.5) / 0.3
        return base_score * factor
    else:
        # 신뢰도 높음: 기본값 유지
        return base_score
```

### 금융 도메인 가중치

```
금융 데이터 언급: ×1.2
공격 문맥 (예: unauthorized_access): ×1.15
```

### 의사결정 매핑

```python
if 0 <= a5_score <= 30:
    a5_decision = "Allow"
elif 31 <= a5_score <= 50:
    a5_decision = "Conditional"
elif 51 <= a5_score <= 80:
    a5_decision = "Approval"
else:  # 81-100
    a5_decision = "Block"
```

### 예시

**프롬프트**: "SELECT * FROM customers; DROP TABLE users;"

```
Step 1: base_severity = 95 (SQL Injection - CRITICAL)
Step 2: multiplier = 1.2 (금융 데이터)
Step 3: adjusted_score = 95 × 1.2 = 114 → cap 100
Step 4: keyword_boost = 2 × 2 = 4 ("SELECT", "DROP")
Step 5: confidence = 0.95 (높음)
        final_score = 100 (신뢰도 높음, 기본값 유지)

A5_SCORE = 100 → "Block"
```

---

## 🎯 최종 의사결정 공식 (Orchestrator)

### Voting System

```
각 Agent 의사결정 → 점수 할당:
- Allow:      5점
- Conditional: 10점
- Approval:   25점
- Block:      40점

총점 = A1_voting_points + A2_voting_points + A3_voting_points + A5_voting_points
최종점수 = min(총점, 100) [cap at 100]
```

### 최종 결정 매핑

```python
if 0 <= final_score <= 20:
    final_decision = "Allow"
elif 21 <= final_score <= 60:
    final_decision = "Conditional"
elif 61 <= final_score <= 85:
    final_decision = "Approval"
else:  # 86-100
    final_decision = "Block"
```

---

## 📋 요약 테이블

| Agent | 점수 계산 방식 | 범위 | 핵심 요소 |
|-------|-----------|------|---------|
| **A1** | 최대 심각도 | 0-100 | 데이터 등급 심각도 |
| **A2** | 합산 (의도+부서+직급+공격) | 0-100 | 의도, 부서, 직급 신뢰도, 공격 |
| **A3** | JSON 규정 severity | 0-100 | 법규 위반 여부 |
| **A5** | OWASP 기준 + 신뢰도 곡선 | 0-100 | 공격 기법, 신뢰도 |
| **최종** | Voting System | 0-100 | 4가지 Agent 의사결정 |

---

**작성자**: Claude Code  
**검토 상태**: ✅ 완료  
**마지막 수정**: 2026-07-23
