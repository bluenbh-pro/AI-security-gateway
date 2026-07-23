"""
Risk Score 계산 모듈 (최종 구현)

위험도 계산 공식 (2단계):
1. [사전 판단] Agent 5 (공격탐지): 공격 탐지 → 즉시 100점 (차단)
2. [가중합] 공격 미탐지:
   Risk Score = (Data Sensitivity × 0.40) + (Context Risk × 0.30) +
                (Policy Risk × 0.30)

모든 입력 점수: 0-100 (높을수록 위험도 높음)
- Data Sensitivity: Agent 1에서 sensitivity_level 정규화 (극비=100, 대외비=50, ...)
- Context Risk: Agent 2에서 계산 (risk_score = 100 - user_score)
- Policy Risk: Agent 3에서 계산 (policy_risk_score = violation_count × 10)

최종 출력 범위: 0-100

의사결정 단계:
- 0-20: 허용
- 21-40: 조건부허용
- 41-60: 마스킹
- 61-80: 승인요청
- 81-100: 차단
"""

from typing import Dict, Any


class RiskScorer:
    """위험도 점수 계산 (개선된 버전)"""

    # 가중치 설정 (Agent 5는 사전 판단으로 별도)
    # NOTE: Agent 3 정책 데이터 추가 전까지 policy_risk를 0으로 설정
    # 가중치 정규화: 40/(40+30) = 0.57, 30/(40+30) = 0.43
    WEIGHTS = {
        "data_sensitivity": 0.57,      # Agent 1: 데이터 민감도 (40% → 57%)
        "context_risk": 0.43,          # Agent 2: 컨텍스트 위험도 (30% → 43%)
        "policy_risk": 0.00            # Agent 3: 정책 위험도 (임시 비활성화, 30% → 0%)
    }

    # 의사결정 4단계 Tier (사용자 정의)
    # 0-30: 허용 (30%)
    # 31-55: 조건부허용 (25%) - 조건부 + 마스킹
    # 56-85: 승인요청 (30%)
    # 86-100: 차단 (15%)
    DECISION_TIERS = {
        "허용": (0, 30),
        "조건부허용": (31, 55),
        "승인요청": (56, 85),
        "차단": (86, 100)
    }

    def calculate(self, agents_output: Dict[str, Any]) -> float:
        """
        종합 위험도 점수 계산 (2단계)

        **Step 1 [사전 판단]**: Agent 5 공격 탐지
        - 공격 탐지됨 → 즉시 100점 반환 (차단)
        - 공격 미탐지 → Step 2로 진행

        **Step 2 [가중합]**: 3개 에이전트
        Risk Score = (Data Sensitivity × 0.40) + (Context Risk × 0.30) +
                     (Policy Risk × 0.30)

        예시 (공격 탐지):
        입력: {
            "classification": {"sensitivity_level": "극비"},
            "context": {"risk_score": 10},
            "policy": {"policy_risk_score": 0},
            "attack": {"attack_detected": true, "confidence": 0.9}
        }
        출력: 100 (공격 탐지로 즉시 차단)

        예시 (공격 미탐지):
        입력: {
            "classification": {"sensitivity_level": "극비"},
            "context": {"risk_score": 25},
            "policy": {"policy_risk_score": 20},
            "attack": {"attack_detected": false, "confidence": 0.1}
        }
        출력: (100×0.4) + (25×0.3) + (20×0.3) = 65점
        """

        # ========== Step 1: 공격 탐지 사전 판단 [최우선] ==========
        attack_result = agents_output.get("attack", {})

        # 공격 결과가 있고 탐지된 경우
        if attack_result and isinstance(attack_result, dict):
            is_attack = attack_result.get("attack_detected", False)
            if is_attack:
                confidence = float(attack_result.get("confidence", 0.8))
                # 신뢰도 80% 이상이면 즉시 100점 (차단)
                if confidence >= 0.8:
                    return 100.0

        # ========== Step 2: 3개 에이전트 기반 가중합 ==========

        # 1. Agent 1: 데이터 민감도 정규화 (0-100)
        data_sensitivity = self._normalize_sensitivity(
            agents_output.get("classification", {}).get("sensitivity_level", "내부")
        )

        # 2. Agent 2: 이미 계산된 위험도 점수 (0-100, 직접 사용!)
        context_risk = agents_output.get("context", {}).get("risk_score", 50)
        # 혹시 agent_2가 아직 기존 형식을 사용하는 경우 대비
        if context_risk is None:
            user_score = agents_output.get("context", {}).get("user_score", 50)
            context_risk = 100 - user_score
        context_risk = float(context_risk)

        # 3. Agent 3: 이미 계산된 정책 위험도 점수 (0-100, 직접 사용!)
        policy_risk = agents_output.get("policy", {}).get("policy_risk_score", 0)
        # 혹시 agent_3이 아직 기존 형식을 사용하는 경우 대비
        if policy_risk is None:
            # 기존: policy_violation (bool) 형식
            policy_violation = agents_output.get("policy", {}).get("policy_violation", False)
            policy_risk = 80.0 if policy_violation else 0.0
        policy_risk = float(policy_risk)

        # 4. 최종 가중합 계산
        weighted_score = (
            data_sensitivity * self.WEIGHTS["data_sensitivity"] +
            context_risk * self.WEIGHTS["context_risk"] +
            policy_risk * self.WEIGHTS["policy_risk"]
        )

        # 5. 최종 점수 반환 (0-100 범위)
        return min(100, max(0, weighted_score))

    def _normalize_sensitivity(self, sensitivity_level: str) -> float:
        """
        민감도 수준 → 0-100 정규화 (5단계)

        매핑:
        - 극비: 100 (최고 위험)
        - 대외비: 50
        - 신용정보: 85
        - 개인정보: 85
        - 민감정보: 70
        - 기본값: 50 (대외비 수준)
        """
        sensitivity_map = {
            "극비": 100,          # 최고 위험
            "대외비": 50,         # ← 변경 (80 → 50)
            "신용정보": 85,       # ← 변경 (70 → 85)
            "개인정보": 85,       # ← 변경 (60 → 85)
            "민감정보": 70,       # ← 변경 (50 → 70)
        }
        return sensitivity_map.get(sensitivity_level, 50)  # 기본값: 대외비 (50)

    def _normalize_policy_violation(self, policy_violation: bool, approval_required: bool) -> float:
        """
        정책 위반 위험도 정규화

        논리:
        - 정책 위반 없음: 0 (위험 없음)
        - 정책 위반: 80 (높은 위험)
        - 승인 필요: 추가 +20 (상한 100)
        """
        if not policy_violation and not approval_required:
            return 0.0

        risk_score = 0.0

        if policy_violation:
            risk_score = 80.0

        if approval_required:
            risk_score += 20.0

        return min(100, risk_score)

    def _normalize_user_trust(self, user_score: float, legitimacy: str) -> float:
        """
        사용자 신뢰도 기반 위험도 정규화

        논리:
        - user_score (0-100): 높을수록 신뢰도 높음 → 위험도 낮음
        - legitimacy: "의심"이면 위험도 증가

        계산:
        - base_risk = 100 - user_score
        - legitimacy가 "의심"이면 +10 (상한 100)
        """
        base_risk = 100 - user_score

        if legitimacy == "의심":
            base_risk += 10

        return min(100, max(0, base_risk))

    def get_decision(self, risk_score: float) -> Dict[str, Any]:
        """
        위험도 점수 → 의사결정 변환

        risk_score를 DECISION_TIERS와 비교하여 의사결정 단계 반환

        Args:
            risk_score: 0-100 범위의 위험도 점수

        Returns:
            {
                "decision": "허용|조건부허용|마스킹|승인요청|차단",
                "risk_score": score,
                "tier": (min, max)
            }
        """

        for decision_name, (min_score, max_score) in self.DECISION_TIERS.items():
            if min_score <= risk_score <= max_score:
                return {
                    "decision": decision_name,
                    "risk_score": risk_score,
                    "tier": (min_score, max_score)
                }

        # 기본값 (정상)
        return {
            "decision": "허용",
            "risk_score": risk_score,
            "tier": (0, 20)
        }


if __name__ == "__main__":
    scorer = RiskScorer()

    # 테스트
    test_output = {
        "classification": {"sensitivity_level": "극비"},
        "context": {"user_score": 40},
        "policy": {"policy_violation": False},
        "attack": {"attack_detected": True, "confidence": 0.9}
    }

    score = scorer.calculate(test_output)
    decision = scorer.get_decision(score)

    print(f"Risk Score: {score}")
    print(f"Decision: {decision}")
