# Orchestrator State & Node 검토 보고서

**검토일**: 2026-07-23  
**목표**: "부서, 직급, 데이터등급(7개유형)" 외 추가 정보 확인

---

## 📋 Orchestrator State 구조

### OrchestratorState (내부 상태)
```python
# [ESSENTIAL] Agent 점수
- data_sensitivity: float (A1)
- context_risk_score: float (A2)
- violation_severity: float (A3)
- attack_score: float (A5)

# [ESSENTIAL] Agent 의사결정
- a1_decision: str
- a2_decision: str
- a3_decision: str
- a5_decision: str

# 계산 결과
- final_score: float
- final_decision: str

# 추적용
- explanation: str
- execution_log: List[str]
```

---

## 🔄 각 Agent Node 입출력 분석

### ✅ Agent 1: 데이터 분류 (A1)

**입력:**
```python
self.agent_1.classify(prompt)
```
- prompt (프롬프트 텍스트만)

**출력 (A1Output):**
```
- a1_score: float (0-100)
- a1_decision: str
- data_grades: List[str] (7개 등급)
- severity_mapping: Dict[str, int]
- confidence: float
```

**평가:** ✅ 깔끔함. 부서/직급 정보 없음 (의도적 설계)

---

### ✅ Agent 2: 컨텍스트 위험도 (A2)

**입력:**
```python
self.agent_2.calculate_context_risk(
    prompt=prompt,
    user_context=user_context,           # 👈 부서, 직급
    data_types=a1_result.data_grades,    # 👈 데이터 등급
    sensitivity_level=a1_result.data_grades[0],
    a1_score=data_sensitivity            # A1 점수
)
```

**정보 흐름:**
- prompt ✅
- user_context: {department, role} ✅
- data_types: 데이터 등급들 ✅
- sensitivity_level: 데이터 등급 ✅
- a1_score: A1 점수 ✅

**출력:**
```
- a2_score: float (0-100)
- a2_decision: str
- context_risk_score: float (호환성)
- purpose_risk: float
- dept_appropriateness: float
- role_credibility: float
- semantic_attack_boost: float
```

**평가:** ✅ 명확함. 필요한 정보만 전달

---

### ⚠️ Agent 3: 정책 위반 검증 (A3)

**입력:**
```python
a3_result = self.agent_3.detect_from_agent1_result(
    agent1_result=agent1_dict,
    agent2_result=agent2_dict,
    prompt=prompt
)
```

**agent1_dict 내용:**
```python
{
    "data_types": a1_result.data_grades,              # ✅ 필요
    "sensitivity_level": a1_result.data_grades[0],    # ✅ 필요
    "risk_score": data_sensitivity,                   # ✅ 필요
    "confidence": a1_result.confidence,               # ⚠️ 추가 정보
    "analysis_details": {                             # ⚠️ 추가 정보
        "grades": a1_result.data_grades,
        "severity_mapping": a1_result.severity_mapping,
    }
}
```

**agent2_dict 내용:**
```python
{
    "context_risk_score": context_risk_score,         # ✅ 필요
    "analysis_result": a2_result                      # ⚠️ 추가 정보 (전체 dict)
}
```

**출력:**
```
- a3_score: int (0-100)
- a3_decision: str
- has_violation: bool
- violation_type: str
- applicable_laws: List[str]
- violation_articles: List[str]
- violation_severity: int
```

**평가:** ⚠️ **문제점 발견**
- "confidence", "analysis_details" 불필요
- "analysis_result" 전체 전달 비효율
- 필요한 정보만 추출해서 전달해야 함

---

### ✅ Agent 5: 공격 탐지 (A5)

**입력:**
```python
a5_result = self.agent_5.detect_attack(prompt)
```
- prompt (프롬프트 텍스트만)

**출력 (AttackResult):**
```
- a5_score: float (0-100)
- a5_decision: str
- attack_detected: bool
- attack_type: str
- attack_score: float
- [INTERNAL] 기타 상세 정보
```

**평가:** ✅ 깔끔함. 부서/직급 정보 없음 (의도적 설계)

---

## 📊 정보 흐름 요약

| Agent | 부서 | 직급 | 데이터등급(7) | 기타 정보 | 평가 |
|-------|------|------|----------|---------|------|
| A1 | ❌ | ❌ | ❌ | ❌ | ✅ 깔끔 |
| A2 | ✅ | ✅ | ✅ | ✅ | ✅ 필요 |
| A3 | ❌ | ❌ | ✅ | ⚠️ 과다 | ⚠️ 정리 필요 |
| A5 | ❌ | ❌ | ❌ | ❌ | ✅ 깔끔 |

---

## 🔴 발견된 문제

### 1. Agent 3의 과도한 정보 전달

**현재:**
```python
agent1_dict = {
    "data_types": ...,
    "sensitivity_level": ...,
    "risk_score": ...,
    "confidence": ...,           # ⚠️ 불필요
    "analysis_details": {...}    # ⚠️ 불필요
}
```

**개선 제안:**
```python
agent1_dict = {
    "data_types": a1_result.data_grades,
    "sensitivity_level": a1_result.data_grades[0],
    "risk_score": data_sensitivity,
}
```

### 2. Agent 2 결과 전체 전달

**현재:**
```python
agent2_dict = {
    "context_risk_score": context_risk_score,
    "analysis_result": a2_result  # ⚠️ 전체 dict 전달
}
```

**개선 제안:**
```python
agent2_dict = {
    "context_risk_score": context_risk_score,
    "a2_decision": a2_result.get("a2_decision", "Allow")
}
```

---

## ✅ 검토 결론

### 현황
- ✅ A1, A5: 부서/직급 정보 없음 (의도적, 정보 분류/공격 탐지는 맥락 무관)
- ✅ A2: 명확한 정보 전달 (부서, 직급, 데이터등급)
- ⚠️ **A3: 불필요한 정보 과다 포함**

### 핵심 이슈
**"부서, 직급, 데이터등급 외 추가 정보가 들어간 케이스"**
→ **A3가 agent1_dict와 agent2_dict를 통해 불필요한 메타데이터 수신**

### 권장 개선사항
1. A3의 `detect_from_agent1_result()` 입력 최소화
2. confidence, analysis_details 제거
3. a2_result 전체가 아닌 필요한 필드만 전달

---

**작성자**: Claude Code  
**상태**: 검토 완료, 개선 필요 ⚠️
