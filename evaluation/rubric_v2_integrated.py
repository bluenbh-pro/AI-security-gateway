#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Rubric V2: 통합 평가 기준 (3가지 Agent 점수 조합)

프로젝트 목표:
"임직원이 LLM에 prompt + 파일을 입력할 때,
 데이터 민감도 + 정책 준수 + 요청자 신뢰도를 종합적으로 판단하여
 LLM 전달 가능 여부와 위험도를 결정"

평가 3가지 차원:
1. Data Sensitivity (Agent 1): 감지된 데이터의 민감도 (0-100)
2. Policy Risk (Agent 3): 법령/정책 준수 위험도 (0-100)
3. Context Risk (Agent 2): 요청자의 신뢰도/정당성 (0-100)

최종 점수: 3가지 차원의 가중치 합
"""

from typing import Dict, Any, Tuple


class RubricV2Integrated:
    """통합 Rubric V2"""

    def __init__(self, agent3_detector=None):
        """
        초기화

        Args:
            agent3_detector: PolicyDetector 인스턴스 (정책 위반 감지용)
        """
        self.agent3 = agent3_detector
        # 가중치
        self.weights = {
            "data_sensitivity": 0.40,
            "policy_risk": 0.30,
            "context_risk": 0.30
        }

    def evaluate(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        케이스 평가 (3가지 Agent 점수 조합)

        Args:
            test_case: {
                "case_id": str,
                "prompt": str,
                "data_types": list,
                "sensitivity_level": str,  # 무난/주의/고위험
                "attack_detected": bool,
                "user_context": {"role": str, "department": str},
                ... (기타)
            }

        Returns:
            {
                "risk_score": float (0-100),
                "decision": str,
                "components": {
                    "agent1_score": float,
                    "agent3_score": float,
                    "agent2_score": float
                },
                "explanation": str
            }
        """
        # 공격 감지: 즉시 Block
        if test_case.get("attack_detected", False):
            return {
                "risk_score": 100,
                "decision": "Block",
                "components": {
                    "agent1_score": 100,
                    "agent3_score": 100,
                    "agent2_score": 100
                },
                "explanation": "공격 탐지됨"
            }

        # Agent 1: 데이터 민감도 (0-100)
        agent1_score = self._calculate_agent1_score(test_case)

        # Agent 3: 정책 위험도 (0-100)
        agent3_score = self._calculate_agent3_score(test_case)

        # Agent 2: 컨텍스트 위험도 (0-100)
        agent2_score = self._calculate_agent2_score(test_case)

        # 최종 점수: 가중치 조합
        final_score = (
            agent1_score * self.weights["data_sensitivity"] +
            agent3_score * self.weights["policy_risk"] +
            agent2_score * self.weights["context_risk"]
        )

        # 의사결정
        decision = self._score_to_decision(final_score)

        return {
            "risk_score": round(final_score, 2),
            "decision": decision,
            "components": {
                "agent1_score": round(agent1_score, 2),
                "agent3_score": round(agent3_score, 2),
                "agent2_score": round(agent2_score, 2)
            },
            "explanation": self._generate_explanation(
                agent1_score, agent3_score, agent2_score
            )
        }

    def _calculate_agent1_score(self, test_case: Dict[str, Any]) -> float:
        """
        Agent 1: 데이터 민감도 (0-100)

        민감도 레벨:
        - 무난: 15점
        - 주의: 50점
        - 고위험: 85점
        """
        sensitivity_map = {
            "무난": 15,
            "주의": 50,
            "고위험": 85
        }
        sensitivity_level = test_case.get("sensitivity_level", "무난")
        return float(sensitivity_map.get(sensitivity_level, 15))

    def _calculate_agent3_score(self, test_case: Dict[str, Any]) -> float:
        """
        Agent 3: 정책 위험도 (0-100)

        방법 1: Agent 3 인스턴스가 있으면 호출
        방법 2: 없으면 데이터 타입 기반 추정
        """
        if self.agent3:
            # Agent 3 호출
            agent1_result = {
                "data_types": test_case.get("data_types", ["general"]),
                "sensitivity_level": test_case.get("sensitivity_level", "무난"),
                "risk_score": test_case.get("risk_score", 0)
            }
            policy_violation = self.agent3.detect_from_agent1_result(agent1_result)
            return policy_violation.policy_risk_score
        else:
            # 데이터 타입 기반 추정
            data_types = test_case.get("data_types", [])
            if "general" in data_types or not data_types:
                return 0.0

            # 민감한 데이터 타입 포함 여부
            sensitive_types = {
                "credit_data": 35,
                "personal_data": 30,
                "financial_data": 32,
                "transaction_data": 33,
                "document": 28,
                "source_code": 34
            }

            max_score = 0
            for dtype in data_types:
                if dtype in sensitive_types:
                    max_score = max(max_score, sensitive_types[dtype])

            # Sensitivity 레벨에 따른 배수
            sensitivity_level = test_case.get("sensitivity_level", "무난")
            multipliers = {"무난": 1, "주의": 2, "고위험": 3}
            multiplier = multipliers.get(sensitivity_level, 1)

            score = max_score * multiplier
            return min(score, 100.0)

    def _calculate_agent2_score(self, test_case: Dict[str, Any]) -> float:
        """
        Agent 2: 컨텍스트 위험도 (0-100)

        직급별 신뢰도 점수 (낮을수록 신뢰도 높음):
        - 임원: 10점 (신뢰도 최고)
        - 파트장: 30점 (신뢰도 높음)
        - 프로: 50점 (신뢰도 중간)
        - 외주인력: 80점 (신뢰도 낮음)

        부서별 조정:
        - 재무/인사: -20점 (신뢰도 높음)
        - IT보안: -15점
        - 기타: 0점
        """
        user_context = test_case.get("user_context", {})
        role = user_context.get("role", "프로")
        department = user_context.get("department", "기타")

        # 직급 기반 기본 점수 (정의된 4개 직급만)
        role_scores = {
            "임원": 10,
            "파트장": 30,
            "프로": 50,
            "외주인력": 80,
        }
        base_score = float(role_scores.get(role, 50))

        # 부서별 조정 (정의된 14개 부서명만 사용)
        dept_adjustments = {
            "재경팀": -20,     # 높은 신뢰도
            "인사팀": -20,     # 높은 신뢰도
            "IT보안팀": -15,   # 높은 신뢰도
        }
        adjustment = float(dept_adjustments.get(department, 0))

        score = base_score + adjustment
        return max(0, min(score, 100))

    def _score_to_decision(self, score: float) -> str:
        """
        점수를 의사결정으로 변환

        0-30: Allow
        31-55: Conditional Allow
        56-85: Approval Required
        86-100: Block
        """
        if score <= 30:
            return "Allow"
        elif score <= 55:
            return "Conditional Allow"
        elif score <= 85:
            return "Approval Required"
        else:
            return "Block"

    def _generate_explanation(
        self,
        agent1_score: float,
        agent3_score: float,
        agent2_score: float
    ) -> str:
        """설명 생성"""
        factors = []

        if agent1_score >= 50:
            factors.append(f"높은 데이터 민감도({agent1_score:.0f})")
        if agent3_score >= 50:
            factors.append(f"정책 위반 위험({agent3_score:.0f})")
        if agent2_score >= 50:
            factors.append(f"낮은 요청자 신뢰도({agent2_score:.0f})")

        if not factors:
            return "안전한 요청"

        return " | ".join(factors)


# 테스트
if __name__ == "__main__":
    rubric = RubricV2Integrated()

    test_cases = [
        {
            "case_id": "TC_1",
            "sensitivity_level": "무난",
            "data_types": ["general"],
            "attack_detected": False,
            "user_context": {"role": "프로", "department": "재무팀"}
        },
        {
            "case_id": "TC_2",
            "sensitivity_level": "고위험",
            "data_types": ["credit_data", "personal_data"],
            "attack_detected": False,
            "user_context": {"role": "외주인력", "department": "기타"}
        },
        {
            "case_id": "TC_3",
            "sensitivity_level": "주의",
            "data_types": ["document"],
            "attack_detected": False,
            "user_context": {"role": "임원", "department": "기타"}
        }
    ]

    print("=" * 80)
    print("[RUBRIC V2] Integrated Rubric Evaluation")
    print("=" * 80)

    for test_case in test_cases:
        result = rubric.evaluate(test_case)
        print(f"\n[{test_case['case_id']}]")
        print(f"  Data Sensitivity: {result['components']['agent1_score']:.0f}")
        print(f"  Policy Risk: {result['components']['agent3_score']:.0f}")
        print(f"  Context Risk: {result['components']['agent2_score']:.0f}")
        print(f"  → Final Score: {result['risk_score']:.0f}")
        print(f"  → Decision: {result['decision']}")
        print(f"  → Explanation: {result['explanation']}")
