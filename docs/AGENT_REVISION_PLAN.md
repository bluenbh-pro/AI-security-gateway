# 【Agent 1-5 수정 계획】

**작성일**: 2026-06-23  
**목표**: 원래 프로젝트 목표와 사용자 의도에 정확히 부합하는 5개 에이전트로 재설계  
**기간**: 1-2일 (Phase 1)

---

## 📋 **수정 요약**

| Agent | 현재 상태 | 필요 수정 | 우선순위 | 예상 시간 |
|-------|---------|---------|---------|----------|
| **Agent 1** | ⚠️ 부분완성 | 금융특화 강화 + LLM 동적생성 | 🔴 높음 | 2h |
| **Agent 2** | ✅ 완성 | 역할 명확화 (신뢰도 + 요청적정성) | 🔴 높음 | 1h |
| **Agent 3** | ❌ 잘못됨 | 권한검증 → 법령/지침 위반 검증으로 전환 | 🔴 최우선 | 2h |
| **Agent 4** | ✅ 완성 | 검토만 (문제없음) | 🟡 중간 | 0.5h |
| **Agent 5** | ⚠️ 부분완성 | FinRED 공격패턴 추가 | 🟡 중간 | 1h |

**총 예상 시간**: 6.5시간

---

## 🔴 **Agent 1: 데이터분류 (금융특화 강화)**

### 현재 상태
```python
# data/taxonomy.json: 30개 카테고리
# 문제: 일반적인 분류만 함, 금융 도메인 심화 부족
```

### 수정사항

#### 1. Taxonomy 확장 (30 → 50개)
```json
// 추가 카테고리 (20개)
{
  "PII_003": "금융계좌소유자정보",  // 추가
  "FIN_003": "신용거래정보",         // 추가
  "FIN_004": "자산운용정보",         // 추가
  "FIN_005": "대출정보",             // 추가
  "FIN_006": "보험정보",             // 추가
  "REG_001": "규제위반사항",         // 추가 (Agent 3과 연계)
  "INT_002": "프로젝트정보",
  "INT_003": "고객프로필",
  "INT_004": "거래상대방정보",
  ... 20개 추가
}
```

#### 2. LLM 기반 동적 분류 추가
```python
# 기존: Taxonomy에 없는 데이터 → "없음" 반환
# 변경: LLM이 새로운 카테고리 동적으로 생성

class DataClassificationAgent:
    def _llm_dynamic_classification(self, text: str) -> Dict:
        """
        Taxonomy에 없는 새로운 데이터 타입을 LLM이 동적으로 분류
        
        예:
        입력: "우리 회사의 AI 모델 아키텍처"
        출력: {
            "data_type": "AI모델정보",
            "sensitivity_level": "기밀",
            "new_category": true,  # 새로운 카테고리
            "confidence": 0.85
        }
        """
        pass
```

#### 3. 마스킹 규칙 강화
```python
# 기존: 단순 마스킹
# 변경: 금융특화 마스킹

masking_patterns = {
    "계좌번호": {
        "pattern": r"\d{3,4}-\d{2,3}-\d{4,8}",
        "mask": "****-**-****",
        "type": "financial_account"
    },
    "신용카드": {
        "pattern": r"\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}",
        "mask": "****-****-****-****",
        "type": "credit_card"
    },
    "거래금액": {
        "pattern": r"(\d{1,3}[,\d]*원|\$\d+)",
        "mask": "***,***원",
        "type": "transaction_amount"
    }
}
```

### 수정 파일
- `agents/agent_1_classification.py` (전체 개선)
- `data/taxonomy.json` (카테고리 확장)

---

## 🔴 **Agent 2: 신뢰도 분석 (역할 명확화)**

### 현재 상태
```python
# 부서/직급/시간/접근패턴 기반 신뢰도 계산 ✅
# 하지만 "요청의 적정성"이 명확하지 않음
```

### 수정사항

#### 1. 역할 재정의
```python
class ContextAnalysisAgent:
    """
    역할: 
    1️⃣ 사용자의 신뢰도 평가 (부서, 직급, 패턴)
    2️⃣ 요청의 적정성 평가 (정상적인 업무 질의인가?)
    
    예:
    • 영업팀 김철수가 "고객정보 조회" → 정상 요청 ✓
    • 개발팀 박지훈이 "극비 영업전략" → 의심 요청 ✗
    • HR팀 이순신이 "임직원급여" → 정상 요청 (HR 업무) ✓
    """
    
    def analyze(self, user_id: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        사용자 신뢰도 + 요청 적정성 점수화
        
        Output:
        {
            "user_score": 0-100,              # 사용자 신뢰도
            "request_appropriateness": 0-100, # 요청 적정성 (신규)
            "legitimacy": "정당|의심",        # 종합 판정
            "risk_assessment": "낮음|중간|높음"
        }
        """
```

#### 2. 요청 적정성 평가 로직 추가
```python
def _evaluate_request_appropriateness(self, user_context: Dict) -> float:
    """
    요청이 이 사용자의 정상적인 업무인가?
    
    평가 지표:
    • 부서와의 일관성 (영업팀이 고객정보 조회? 정상)
    • 접근 빈도와의 일관성 (평소 이런 요청을 하나?)
    • 요청 규모의 타당성 (한두 건? 1000건? 비정상)
    • 요청 데이터 타입의 타당성 (현업무와 관련된 데이터?)
    """
    pass
```

### 수정 파일
- `agents/agent_2_context.py` (역할 확대)

---

## 🔴 **Agent 3: 정책검증 (권한 → 법령/지침 검증으로 전환) ⭐ 최우선**

### 현재 상태 (잘못됨)
```python
# 역할: 부서별 접근 권한 검증
# 문제: Agent 2의 신뢰도와 중복, 원래 목표와 다름
```

### 수정사항 (완전히 다시 작성)

#### 1. 역할 변경
```python
class PolicyValidationAgent:
    """
    역할: 요청이 법령/지침을 위반하는가?
    
    검증 대상:
    1️⃣ 법령: FSMA(전자금융감독규정), 개인정보보호법, AI기본법
    2️⃣ 회사지침: .docx 파일로 제공되는 사내 정책
    
    Output:
    {
        "policy_violation": true|false,
        "violation_type": "FSMA|Privacy|AI_Act|Company_Guideline",
        "risk_score": 0-100,
        "reason": "why this is violation",
        "recommendation": "what to do"
    }
    """
```

#### 2. 법령 파일 구조
```
data/regulations/
├─ fsma_requirements.json
│  ├─ 금융감독 규제 항목
│  ├─ "내부자정보 공개 금지"
│  ├─ "개인정보 보호"
│  └─ "거래기록 관리"
│
├─ privacy_law.json
│  ├─ 개인정보보호법 항목
│  ├─ "PII 수집 목적 제한"
│  ├─ "3자 제공 제한"
│  └─ "보유기간 제한"
│
└─ ai_act.json
   ├─ AI기본법 항목
   ├─ "AI 안전성"
   ├─ "투명성"
   └─ "편향성"
```

#### 3. 회사 지침 파일 구조 (나중에 구현)
```
data/guidelines/
├─ samsung_life_guidelines.docx
├─ hanwha_life_guidelines.docx
└─ kb_insurance_guidelines.docx

# 파싱 로직 (추후 "정보보호QA" 소스코드 활용)
# python-docx로 .docx 읽고
# 정책 항목 추출 → JSON 변환 → Agent 3에서 매칭
```

#### 4. 구현 로직
```python
def validate(self, data_type: str, user_context: Dict[str, Any], user_input: str) -> Dict[str, Any]:
    """
    3단계 검증:
    1. 법령 위반 여부 확인
    2. 회사지침 위반 여부 확인
    3. LLM으로 종합 평가
    """
    # Step 1: 법령 검증
    fsma_violation = self._check_fsma(data_type, user_input)
    privacy_violation = self._check_privacy_law(data_type)
    ai_act_violation = self._check_ai_act(data_type)
    
    # Step 2: 회사 지침 검증 (나중에)
    guideline_violation = self._check_company_guideline(data_type, user_context)
    
    # Step 3: 최종 판정
    if any([fsma_violation, privacy_violation, ai_act_violation, guideline_violation]):
        return {
            "policy_violation": True,
            "violation_type": self._determine_violation_type(...),
            "risk_score": self._calculate_risk(...)
        }
    
    return {"policy_violation": False, ...}
```

### 수정 파일
- `agents/agent_3_policy.py` (완전 재작성)
- `data/regulations/fsma_requirements.json` (신규)
- `data/regulations/privacy_law.json` (신규)
- `data/regulations/ai_act.json` (신규)

---

## 🟡 **Agent 4: 이상행위탐지 (검토만)**

### 현재 상태
```python
# 시간, 빈도, IP, 기기 기반 이상행위 탐지 ✅
# 구현이 양호함
```

### 검토 결과
✅ 역할이 명확함 (이상 행위 탐지)  
✅ 로직이 이해하기 쉬움  
⚠️ 사소한 개선:
  - 프로필 데이터 하드코딩 제거 → 실제 DB 연동 준비
  - 점수 계산 가중치 명확화

### 수정 파일
- `agents/agent_4_anomaly.py` (매우 작은 개선만)

---

## 🟡 **Agent 5: 기술공격탐지 (FinRED 패턴 추가)**

### 현재 상태
```python
# SQL Injection, XSS, Command Injection 탐지 ✅
# LLM 기반 의미적 분석 ✅
```

### 수정사항

#### 1. FinRED 기반 금융 공격 패턴 추가
```python
# 추가할 공격 유형
financial_attack_patterns = {
    "insider_trading_hint": {
        "keywords": ["내부정보", "미공개정보", "선행거래", "우회"],
        "risk_score": 95
    },
    "fraud_solicitation": {
        "keywords": ["사기", "사칭", "위조", "변조"],
        "risk_score": 90
    },
    "money_laundering_hint": {
        "keywords": ["자금세탁", "의심거래", "구조화"],
        "risk_score": 85
    },
    "regulatory_evasion": {
        "keywords": ["규제회피", "적발회피", "적발탈출"],
        "risk_score": 80
    }
}
```

#### 2. LLM 프롬프트 강화
```python
def _llm_analyze_intent(self, user_input: str) -> Dict[str, Any]:
    """
    프롬프트 추가:
    - 금융사기 의도 탐지
    - 내부자정보 활용 의도
    - 규제회피 의도
    - 자금세탁 의도
    """
    prompt = """
    다음 사용자 입력을 분석하세요. 특히 금융 사기, 내부자정보 활용, 규제회피, 자금세탁 등의 의도를 감지하세요.
    
    [FinRED 기반 평가 기준]
    1. Insider Trading: 미공개정보 활용 의도
    2. Fraud: 사기 행위
    3. Money Laundering: 자금세탁 의도
    4. Regulatory Evasion: 규제 회피
    5. Market Manipulation: 시장 조종
    """
```

### 수정 파일
- `agents/agent_5_attack_detection.py` (금융 패턴 추가)

---

## 📊 **Agent 간 상호작용 명확화**

```
【데이터 흐름】

사용자 입력 (업로드된 문서 또는 질의)
  ↓
[Agent 1] 데이터분류
  ├─ 업로드 문서/질의에 포함된 데이터 타입 분류
  ├─ 민감도 판정 (극비/기밀/내부/공개)
  └─ Output: data_type, sensitivity_level, confidence
  ↓
[Agent 2] 신뢰도분석
  ├─ 사용자 신뢰도 평가 (user_score)
  ├─ 요청 적정성 평가 (request_appropriateness)
  ├─ "이 사용자가 이런 요청을 할 수 있나?"
  └─ Output: user_score (0-100)
  ↓
[Agent 3] 정책검증
  ├─ 요청이 법령 위반하나? (FSMA, 개인정보법, AI법)
  ├─ 요청이 지침 위반하나? (회사별 .docx)
  ├─ "이 요청 자체가 법령/지침을 위반하나?"
  └─ Output: policy_violation (true|false), risk_score (0-100)
  ↓
[Agent 4] 이상행위탐지
  ├─ 사용자 행동 이상 탐지
  ├─ "이 사용자가 평소와 다르게 행동하나?"
  └─ Output: anomaly_score (0-100)
  ↓
[Agent 5] 공격탐지
  ├─ 기술공격 탐지 (병렬)
  ├─ "질의가 공격 시도인가?"
  ├─ SQL Injection, Prompt Injection, 사기 의도 등
  └─ Output: attack_detected (true|false), confidence
  ↓
[RiskScorer]
  ├─ 모든 에이전트 결과 통합
  ├─ 가중합: 45% + 10% + 35% + 10%
  └─ Output: risk_score (0-100)
  ↓
[Decision Maker]
  ├─ 0-20: 허용
  ├─ 21-40: 조건부허용
  ├─ 41-60: 마스킹
  ├─ 61-80: 승인요청
  └─ 81-100: 차단
```

---

## ✅ **체크리스트**

### Phase 1: Agent 수정 (지금)
- [ ] Agent 1: Taxonomy 확장 + LLM 동적생성
- [ ] Agent 2: 요청적정성 평가 로직 추가
- [ ] Agent 3: 법령/지침 검증으로 완전 재작성
- [ ] Agent 4: 소소한 개선
- [ ] Agent 5: FinRED 패턴 추가

### Phase 2: 법령 파일 구성
- [ ] FSMA 요구사항 JSON화
- [ ] 개인정보보호법 요구사항 JSON화
- [ ] AI기본법 요구사항 JSON화

### Phase 3: 회사 지침 처리 준비
- [ ] "정보보호QA" 소스코드 받기
- [ ] .docx 파싱 로직 분석
- [ ] Agent 3에 통합 (나중에)

### Phase 4: 통합 테스트
- [ ] Agent 1-5 단위 테스트
- [ ] end-to-end 파이프라인 테스트

---

## 🎯 **다음 단계**

1. 위 수정사항 리뷰
2. Q&A 있으면 즉시 피드백
3. 본격적인 코드 수정 시작
4. "정보보호QA" 소스코드 준비

