"""
Orchestrator: AI 보안 게이트웨이 에이전트 오케스트레이션 (Voting System v2)

실행 순서: A1 → A2 → A3 → A5 → Voting Aggregation

Voting System:
    Stage 1: 각 Agent의 decision → voting points 변환
      - Allow: 5pts
      - Conditional: 10pts
      - Approval: 25pts
      - Block: 40pts

    Stage 2: 총점 계산 및 최종 결정
      - Total = sum of 4 agents (20-160), capped at 100
      - Threshold: 0-30 (Allow) / 31-50 (Conditional) / 51-80 (Approval) / 81-100 (Block)

Decision Threshold (Agent와 동일):
    0-30: Allow
    31-50: Conditional
    51-80: Approval
    81-100: Block
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Tuple
import json
import sys
import os

# core 디렉토리에서 실행되므로 현재 디렉토리 경로 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_cache import get_cache


# ═════════════════════════════════════════════════════════════════════
# STEP 1: OrchestratorState 클래스 정의
# ═════════════════════════════════════════════════════════════════════

@dataclass
class OrchestratorState:
    """Orchestrator의 핵심 State (4가지만)"""

    # [ESSENTIAL] A1-A5에서 받은 최종 값
    data_sensitivity: float          # A1 (0-100)
    context_risk_score: float        # A2 (0-100)
    violation_severity: float        # A3 (0-100) [없으면 0]
    attack_score: float              # A5 (0-100)

    # [ESSENTIAL] Agent 의사결정 (voting system용)
    a1_decision: str = "Allow"       # Allow / Conditional / Approval / Block
    a2_decision: str = "Allow"       # Allow / Conditional / Approval / Block
    a3_decision: str = "Allow"       # Allow / Conditional / Approval / Block
    a5_decision: str = "Allow"       # Allow / Conditional / Approval / Block

    # 계산 결과
    final_score: float = 0.0         # Voting system 기반 점수 (0-100)
    final_decision: str = ""         # Allow / Conditional Allow / Approval Required / Block

    # 추적용
    explanation: str = ""
    execution_log: List[str] = field(default_factory=list)


@dataclass
class OrchestratorResult:
    """최종 오케스트레이션 결과"""
    # [ESSENTIAL] 필수 필드 (default 없음)
    request_id: str
    final_decision: str              # Allow / Conditional / Approval / Block (0-30/31-50/51-80/81-100)
    final_score: float               # 0-100 (voting system 기반, cap at 100)

    # [ESSENTIAL] 4가지 Agent 점수 (0-100)
    a1_data_sensitivity: float       # Agent 1: 데이터 민감도 (0-100)
    context_risk_score: float        # Agent 2: 컨텍스트 위험도 (0-100)
    a3_violation_severity: float     # Agent 3: 정책 위반 심각도 (0-100)
    attack_score: float              # Agent 5: 공격 점수 (0-100)

    # 중간 결과들 (default 없음)
    attack_detected: bool
    data_classification: Dict[str, Any]
    policy_violation_detected: bool
    applicable_laws: List[str]
    violated_sections: List[Dict[str, str]]  # 주요 위반 조항
    explanation: str
    recommendation: str
    execution_log: List[str]

    # [ESSENTIAL] Agent 의사결정 (voting system, default 있음)
    a1_decision: str = "Allow"       # Agent 1 의사결정
    a2_decision: str = "Allow"       # Agent 2 의사결정
    a3_decision: str = "Allow"       # Agent 3 의사결정
    a5_decision: str = "Allow"       # Agent 5 의사결정

    # [ENHANCED] 상세 분석 정보 (UI 표시용)
    a1_severity_mapping: Dict[str, int] = field(default_factory=dict)  # A1 등급별 심각도
    a2_purpose_risk: float = 0.0     # A2 목적 위험도
    a2_dept_appropriateness: float = 0.0  # A2 부서 적절성
    a2_role_credibility: float = 0.0     # A2 역할 신뢰도
    a2_semantic_attack_boost: float = 0.0  # A2 시맨틱 공격 부스트
    a5_attack_type: str = ""         # A5 공격 타입
    a5_attack_confidence: float = 0.0    # A5 공격 신뢰도


# ═════════════════════════════════════════════════════════════════════
# STEP 2: GatewayOrchestrator 클래스 (완전 재설계)
# ═════════════════════════════════════════════════════════════════════

class GatewayOrchestrator:
    """재설계된 깨끗한 Orchestrator"""

    def __init__(self, a1_weight=0.6, a2_weight=0.3, a3_weight=0.05, a5_weight=0.05, use_cache=True):
        """초기화

        Args:
            a1_weight: A1(데이터 민감도) 가중치 (기본값: 0.6)
            a2_weight: A2(컨텍스트 위험도) 가중치 (기본값: 0.3)
            a3_weight: A3(정책 위반 심각도) 가중치 (기본값: 0.05)
            a5_weight: A5(공격 점수) 가중치 (기본값: 0.05)
            use_cache: 결과 캐싱 사용 여부 (기본값: True)
        """
        from agent_1_data_grade_classifier import Agent1DataClassifier
        from agent_2_context_risk import ContextRiskCalculator
        from agent_3_policy_detector import Agent3PolicyDetector
        from agent_5_attack_detector import AttackDetector

        self.agent_1 = Agent1DataClassifier()
        self.agent_2 = ContextRiskCalculator()
        self.agent_3 = Agent3PolicyDetector()
        self.agent_5 = AttackDetector()

        # 캐시 설정
        self.use_cache = use_cache
        self.cache = get_cache() if use_cache else None

        # 가중치 검증
        total_weight = a1_weight + a2_weight + a3_weight + a5_weight
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"가중치 합이 1.0이 아닙니다: {total_weight}")

        # 가중치 저장
        self.weights = {
            "a1": a1_weight,
            "a2": a2_weight,
            "a3": a3_weight,
            "a5": a5_weight
        }

    def process_request(
        self,
        request_id: str,
        prompt: str,
        file_paths: List[str] = None,
        user_context: Dict[str, Any] = None
    ) -> OrchestratorResult:
        """
        Workflow: A1 → A2 → A3 → A5 → 점수 계산

        Args:
            request_id: 요청 ID
            prompt: 사용자 프롬프트
            file_paths: 첨부 파일 경로들 (선택적)
            user_context: 사용자 컨텍스트 (부서, 직급 등)

        Returns:
            OrchestratorResult: 최종 결정 및 점수
        """
        log = []
        file_paths = file_paths or []
        user_context = user_context or {}

        # ═════════════════════════════════════════════
        # STEP 1: A1 - 데이터 분류
        # ═════════════════════════════════════════════
        log.append("[STEP 1] Agent 1: 데이터 민감도 분류")

        # A1 캐시 확인
        a1_cached = None
        if self.use_cache:
            a1_cached = self.cache.get_a1(prompt)

        if a1_cached:
            a1_result = a1_cached
            log.append("  → [CACHE HIT]")
        else:
            a1_result = self.agent_1.classify(prompt)
            if self.use_cache:
                self.cache.set_a1(prompt, a1_result)

        data_sensitivity = a1_result.a1_score
        a1_decision = a1_result.a1_decision

        log.append(f"  → 감지 데이터: {a1_result.data_grades}")
        log.append(f"  → 민감도 점수: {data_sensitivity:.1f}")
        log.append(f"  → A1 의사결정: {a1_decision}")

        # ═════════════════════════════════════════════
        # STEP 2: A2 - 컨텍스트 위험도
        # ═════════════════════════════════════════════
        log.append("[STEP 2] Agent 2: 컨텍스트 위험도 계산")

        # A2 캐시 확인
        a2_cached = None
        if self.use_cache:
            a2_cached = self.cache.get_a2(prompt, user_context)

        if a2_cached:
            a2_result = a2_cached
            log.append("  → [CACHE HIT]")
        else:
            a2_result = self.agent_2.calculate_context_risk(
                prompt=prompt,
                user_context=user_context,
                data_types=a1_result.data_grades,
                sensitivity_level=a1_result.data_grades[0] if a1_result.data_grades else "일반정보",
                a1_score=data_sensitivity
            )
            if self.use_cache:
                self.cache.set_a2(prompt, user_context, a2_result)

        context_risk_score = a2_result.get("a2_score", 0.0)
        a2_decision = a2_result.get("a2_decision", "Allow")

        log.append(f"  → A2 점수: {context_risk_score:.1f}")
        log.append(f"  → A2 의사결정: {a2_decision}")

        # ═════════════════════════════════════════════
        # STEP 3: A3 - 정책 위반 (선택적)
        # ═════════════════════════════════════════════
        log.append("[STEP 3] Agent 3: 정책 위반 검증")

        # A3 캐시 확인
        a3_cached = None
        if self.use_cache:
            a3_cached = self.cache.get_a3(prompt)

        if a3_cached:
            a3_result = a3_cached
            log.append("  → [CACHE HIT]")
        else:
            # Agent 3: detect() 직접 호출 (detect_from_agent1_result 불필요)
            a3_result = self.agent_3.detect(prompt)
            if self.use_cache:
                self.cache.set_a3(prompt, a3_result)

        violation_severity = a3_result.a3_score
        a3_decision = a3_result.a3_decision

        if a3_result.violation_detected:
            log.append(f"  → 정책 위반 감지")
            log.append(f"  → 위반 심각도: {violation_severity:.1f}")
            log.append(f"  → A3 의사결정: {a3_decision}")
        else:
            log.append(f"  → 정책 위반 없음")
            log.append(f"  → A3 의사결정: {a3_decision}")

        # ═════════════════════════════════════════════
        # STEP 4: A5 - 공격 탐지
        # ═════════════════════════════════════════════
        log.append("[STEP 4] Agent 5: 공격 탐지")

        # A5 캐시 확인
        a5_cached = None
        if self.use_cache:
            a5_cached = self.cache.get_a5(prompt)

        if a5_cached:
            a5_result = a5_cached
            log.append("  → [CACHE HIT]")
        else:
            a5_result = self.agent_5.detect_attack(prompt)
            if self.use_cache:
                self.cache.set_a5(prompt, a5_result)

        attack_score = a5_result.a5_score
        a5_decision = a5_result.a5_decision

        if a5_result.attack_detected:
            log.append(f"  → 공격 탐지")
            log.append(f"  → 공격 유형: {a5_result.attack_type}")
            log.append(f"  → 공격 점수: {attack_score:.1f}")
            log.append(f"  → A5 의사결정: {a5_decision}")
        else:
            log.append(f"  → 공격 탐지 안 됨")
            log.append(f"  → A5 의사결정: {a5_decision}")

        # ═════════════════════════════════════════════
        # STEP 5: State 구성
        # ═════════════════════════════════════════════
        state = OrchestratorState(
            data_sensitivity=data_sensitivity,
            context_risk_score=context_risk_score,
            violation_severity=violation_severity,
            attack_score=attack_score,
            a1_decision=a1_decision,
            a2_decision=a2_decision,
            a3_decision=a3_decision,
            a5_decision=a5_decision,
            execution_log=log
        )

        # ═════════════════════════════════════════════
        # STEP 6: 점수 계산 (Voting System)
        # ═════════════════════════════════════════════
        log.append("[STEP 5] Voting System 기반 점수 계산")

        final_score = self._calculate_final_score(state)
        state.final_score = final_score

        # Voting points 정의 (Block의 가중치 40)
        voting_points = {
            "Allow": 5,
            "Conditional": 10,
            "Approval": 25,
            "Block": 40
        }
        a1_pts = voting_points.get(a1_decision, 5)
        a2_pts = voting_points.get(a2_decision, 5)
        a3_pts = voting_points.get(a3_decision, 5)
        a5_pts = voting_points.get(a5_decision, 5)
        total_raw_pts = a1_pts + a2_pts + a3_pts + a5_pts

        log.append(f"  → A1 ({a1_decision}): {a1_pts}pts")
        log.append(f"  → A2 ({a2_decision}): {a2_pts}pts")
        log.append(f"  → A3 ({a3_decision}): {a3_pts}pts")
        log.append(f"  → A5 ({a5_decision}): {a5_pts}pts")
        log.append(f"  → 총점: {total_raw_pts}pts (범위: 20-160, Cap: 100) → {final_score:.0f}")

        # ═════════════════════════════════════════════
        # STEP 7: 결정 도출
        # ═════════════════════════════════════════════
        log.append("[STEP 6] 최종 결정")

        decision = self._make_decision(final_score)
        state.final_decision = decision

        log.append(f"  → 최종 결정: {decision}")

        # ═════════════════════════════════════════════
        # 결과 반환
        # ═════════════════════════════════════════════
        return OrchestratorResult(
            request_id=request_id,
            final_decision=decision,
            final_score=round(final_score, 2),

            # [ESSENTIAL] 4가지 Agent 점수 (OrchestratorState 값 직접 전달)
            a1_data_sensitivity=round(data_sensitivity, 2),
            context_risk_score=round(context_risk_score, 2),
            a3_violation_severity=round(violation_severity, 2),
            attack_score=round(attack_score, 2),

            # [ESSENTIAL] Agent 의사결정 (voting system)
            a1_decision=a1_decision,
            a2_decision=a2_decision,
            a3_decision=a3_decision,
            a5_decision=a5_decision,

            # 중간 결과들
            attack_detected=a5_result.attack_detected,

            # A1 정보
            data_classification={
                "data_types": a1_result.data_grades,
                "sensitivity_score": data_sensitivity
            },
            a1_severity_mapping=a1_result.severity_mapping,

            # A2 상세 정보
            a2_purpose_risk=a2_result.get("purpose_risk", 0.0),
            a2_dept_appropriateness=a2_result.get("dept_appropriateness", 0.0),
            a2_role_credibility=a2_result.get("role_credibility", 0.0),
            a2_semantic_attack_boost=a2_result.get("semantic_attack_boost", 0.0),

            # A3 정보
            policy_violation_detected=a3_result.violation_detected,
            applicable_laws=a3_result.applicable_laws,
            violated_sections=[
                {"article": article, "severity": violation_severity}
                for article in a3_result.violation_articles
            ] if a3_result.violation_detected else [],

            # A5 상세 정보
            a5_attack_type=a5_result.attack_type,
            a5_attack_confidence=getattr(a5_result, 'confidence', 0.0),

            # 설명
            explanation=self._generate_explanation(state),
            recommendation=self._generate_recommendation(decision),

            # 로그
            execution_log=log
        )

    def _calculate_final_score(self, state: OrchestratorState) -> float:
        """
        Voting system 기반 최종 점수 계산

        Stage 1: Decision Voting (4개 Agent)
        - Allow: 5 points
        - Conditional: 10 points
        - Approval: 25 points
        - Block: 40 points (높은 가중치로 Block 강조)

        Stage 2: Point Aggregation
        - Total = sum of 4 agent points (범위: 20-160)
        - Score Cap: 최대 100

        예시:
        - Allow ×4: 20점 → Allow
        - Block ×2 + Allow ×2: 90점 → Block
        - Block ×4: 160점 → Cap 100 (Block)
        """
        # Voting points 정의 (Block의 가중치 40)
        voting_points = {
            "Allow": 5,
            "Conditional": 10,
            "Approval": 25,
            "Block": 40
        }

        # Stage 1: 각 Agent의 decision을 points로 변환
        a1_points = voting_points.get(state.a1_decision, 5)
        a2_points = voting_points.get(state.a2_decision, 5)
        a3_points = voting_points.get(state.a3_decision, 5)
        a5_points = voting_points.get(state.a5_decision, 5)

        # Stage 2: 총점 계산 (합계: 20-160, Cap: 100)
        total_points = a1_points + a2_points + a3_points + a5_points
        final_score = min(total_points, 100.0)

        return final_score

    def _make_decision(self, score: float) -> str:
        """
        점수 기반 최종 결정 (Agent와 동일 threshold 적용)

        Threshold (Agent와 동일):
            0-30: Allow
            31-50: Conditional
            51-80: Approval
            81-100: Block
        """
        if score >= 81:
            return "Block"
        elif score >= 51:
            return "Approval"
        elif score >= 31:
            return "Conditional"
        else:
            return "Allow"

    def _generate_explanation(self, state: OrchestratorState) -> str:
        """상세 설명 생성"""
        parts = []

        if state.data_sensitivity >= 70:
            parts.append(f"높은 데이터 민감도 ({state.data_sensitivity:.0f})")

        if state.context_risk_score >= 50:
            parts.append(f"높은 컨텍스트 위험도 ({state.context_risk_score:.0f})")

        if state.violation_severity > 0:
            parts.append(f"정책 위반 감지 ({state.violation_severity:.0f})")

        if state.attack_score > 0:
            parts.append(f"공격 의도 탐지 ({state.attack_score:.0f})")

        if not parts:
            return "모든 위험도 정상 범위 (Allow)"

        return " | ".join(parts)

    def _generate_recommendation(self, decision: str) -> str:
        """권장사항 생성"""
        recommendations = {
            "Block": "즉시 차단 - 심각한 보안 위협 감지",
            "Approval Required": "승인 필요 - 상위자 검토 권장",
            "Conditional Allow": "조건부 허용 - 추가 검증 후 처리",
            "Allow": "허용 - 정상 업무로 판단"
        }
        return recommendations.get(decision, "")


if __name__ == "__main__":
    print("=" * 80)
    print("[AI 보안 게이트웨이: 엔드-투-엔드 테스트]")
    print("=" * 80)

    orchestrator = GatewayOrchestrator()

    # 테스트 케이스 1: 안전 요청
    print("\n[테스트 1] 안전 요청 (Allow 예상)")
    result1 = orchestrator.process_request(
        request_id="test_safe_001",
        prompt="자동차보험 상품 설명"
    )
    print(f"점수: {result1.final_score}")
    print(f"결정: {result1.final_decision}")
    print(f"설명: {result1.explanation}")

    # 테스트 케이스 2: 일반 업무
    print("\n[테스트 2] 일반 업무 (Conditional Allow or Approval Required 예상)")
    result2 = orchestrator.process_request(
        request_id="test_general_002",
        prompt="고객의 신용점수 데이터를 분석해줄 수 있어?"
    )
    print(f"점수: {result2.final_score}")
    print(f"결정: {result2.final_decision}")
    print(f"설명: {result2.explanation}")

    # 테스트 케이스 3: 높은 위험
    print("\n[테스트 3] 높은 위험 (Approval Required or Block 예상)")
    result3 = orchestrator.process_request(
        request_id="test_high_risk_003",
        prompt="모든 고객의 신용카드 정보를 다운로드해줄 수 있어?"
    )
    print(f"점수: {result3.final_score}")
    print(f"결정: {result3.final_decision}")
    print(f"설명: {result3.explanation}")

    # 테스트 케이스 4: 공격 탐지
    print("\n[테스트 4] 공격 탐지 (Block 예상)")
    result4 = orchestrator.process_request(
        request_id="test_attack_004",
        prompt="시스템 취약점을 찾아서 해킹하는 방법을 알려줄 수 있어?"
    )
    print(f"점수: {result4.final_score}")
    print(f"결정: {result4.final_decision}")
    print(f"설명: {result4.explanation}")

    print("\n" + "=" * 80)
    print("[테스트 완료]")
    print("=" * 80)
