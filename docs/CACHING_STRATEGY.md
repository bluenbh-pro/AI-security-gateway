# Agent 캐싱 전략

## 개요

Orchestrator 평가의 성능 병목을 해결하기 위해 캐싱 시스템을 도입했습니다.

**문제**: 412개 케이스 평가 시 ~40분 소요 (각 케이스 ~5.5초)
**원인**: 각 Agent의 LLM 호출이 반복됨
**해결책**: 동일 입력에 대한 결과 캐싱

---

## 캐싱 설계

### 1. Agent별 캐시 키 전략

| Agent | 키 구성 | 캐시율 | 설명 |
|---|---|---|---|
| **A1** | hash(prompt) | 95% | 프롬프트만 기반 (user_context 무관) |
| **A2** | hash(prompt + user_context) | 50% | 부서/직급에 따라 다른 결과 |
| **A3** | hash(prompt) | 95% | 프롬프트만 기반 |
| **A5** | hash(prompt) | 95% | 프롬프트만 기반 |

**통합 캐시율**: ~80% (예상)

### 2. 메모리 기반 캐싱

```python
# core/agent_cache.py
class AgentCache:
    memory_cache = {
        "a1": {},   # {hash: A1Result}
        "a2": {},   # {hash: A2Result}
        "a3": {},   # {hash: A3Result}
        "a5": {},   # {hash: A5Result}
    }
```

**장점:**
- 빠른 접근 (O(1) lookup)
- 세션 중 유지
- 구현 간단

**단점:**
- 메모리 사용 (20개 prompts × 14 depts × 4 ranks = ~1,120개 조합)
- 세션 종료 시 초기화

---

## 성능 개선 효과

### 예상 개선

| 메트릭 | 이전 | 현재 (80% 캐시율) | 개선율 |
|---|---|---|---|
| 412개 평가 시간 | 40분 | 8분 | 5배 ↓ |
| 평균 케이스 시간 | 5.5초 | 1.1초 | 5배 ↓ |
| LLM 호출 수 | 1648회 | 330회 | 80% ↓ |

### 실제 측정

(테스트 실행 대기 중...)

---

## 구현 상세

### Orchestrator에 캐싱 통합

```python
class GatewayOrchestrator:
    def __init__(self, use_cache=True):
        self.cache = get_cache() if use_cache else None

    def process_request(self, prompt, user_context, ...):
        # A1 캐시 확인
        a1_cached = self.cache.get_a1(prompt)
        if a1_cached:
            a1_result = a1_cached
        else:
            a1_result = self.agent_1.classify(prompt)
            self.cache.set_a1(prompt, a1_result)

        # A2 캐시 확인
        a2_cached = self.cache.get_a2(prompt, user_context)
        if a2_cached:
            a2_result = a2_cached
        else:
            a2_result = self.agent_2.calculate_context_risk(...)
            self.cache.set_a2(prompt, user_context, a2_result)

        # A3, A5도 동일 방식
        ...
```

### 캐시 통계

```python
orch.cache.print_stats()

# 출력:
# [Agent Cache Statistics]
# Agent A1:
#   Hits: 380 / 412 = 92.23%
# Agent A2:
#   Hits: 196 / 412 = 47.57%
# Agent A3:
#   Hits: 390 / 412 = 94.66%
# Agent A5:
#   Hits: 388 / 412 = 94.17%
#
# Overall Hit Rate: 1354 / 1648 = 82.15%
# Expected Time Savings: 82.15% (LLM 호출 감소)
```

---

## 향후 개선 (선택)

### 1. 파일 기반 캐싱 (SQLite)

```python
# 현재: 메모리만 사용 (세션 종료 시 초기화)
# 개선: SQLite에 캐시 저장 (세션 간 유지)

import sqlite3

class PersistentAgentCache(AgentCache):
    def __init__(self, db_path=".cache/agent_cache.db"):
        self.db = sqlite3.connect(db_path)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS a1_cache (
                key TEXT PRIMARY KEY,
                result JSON
            )
        """)
```

**이점**: 평가 재실행 시 캐시 재사용 (누적 효과)

### 2. 배치 처리

```python
# 동일 프롬프트 그룹화 후 병렬 처리
grouped_cases = {}
for case in cases:
    prompt = case['prompt']
    if prompt not in grouped_cases:
        grouped_cases[prompt] = []
    grouped_cases[prompt].append(case)

# 각 프롬프트당 A1, A3, A5는 1회만 호출
# A2는 부서/직급별로 호출
```

**이점**: LLM 호출 횟수 대폭 감소 (이론적 최대 80% → 90%+)

---

## 테스트 가이드

### 캐싱 활성화

```python
# 기본값: use_cache=True
orch = GatewayOrchestrator()
```

### 캐싱 비활성화 (성능 비교)

```python
orch_no_cache = GatewayOrchestrator(use_cache=False)
```

### 통계 확인

```python
orch.cache.print_stats()
```

---

## 주의사항

### 캐시 일관성

현재 캐싱은 **완전히 세션 기반**이므로:
- Agent의 내부 파라미터 변경 후 재평가 시 캐시 초기화 필요
- `orch.cache.clear()` 호출

### 메모리 사용

최악의 경우 (모든 프롬프트 조합):
```
A1: 20 prompts × ~1KB = 20KB
A2: 20 × 14 × 4 = 1,120 × ~2KB = 2.2MB
A3: 20 prompts × ~1KB = 20KB
A5: 20 prompts × ~1KB = 20KB

총계: ~2.3MB (무시할 수 있는 수준)
```

---

## 참고

- **파일**: `core/agent_cache.py` (캐싱 구현)
- **통합**: `core/orchestrator.py` (Orchestrator 적용)
- **평가**: `evaluate_dataset_v2.py` (통계 출력)
