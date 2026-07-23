"""
Agent 3: 정책검증 에이전트

역할: 요청이 법령/지침을 위반하는가?
입력:
  - data_type: Agent 1의 분류 결과 (극비/기밀/내부/공개)
  - user_input: 사용자의 원본 질의
  - user_context: 사용자 정보 (부서, 직급)

출력: {
    "policy_violation": bool,
    "violation_type": str,  # None / "FSMA" / "Privacy_Law" / "AI_Act" / "Company_Guideline"
    "risk_score": 0-100,
    "reason": str,
    "recommendation": str
}

구현: W3 Day 5-7
- 법령 위반 검증 (FSMA, 개인정보보호법, AI기본법)
- 회사지침 위반 검증 (준비, 나중에 .docx 파싱 추가)
- 위반 유형과 위험도 점수화
"""

from typing import Dict, Any
import os
from dotenv import load_dotenv
from openai import OpenAI
import json

load_dotenv()


class PolicyValidationAgent:
    """정책검증 에이전트 - 법령/지침 위반 검증 (권한검증 제거)"""

    def __init__(self):
        """초기화"""
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # 【법령 1】전자금융감독규정 (FSMA: Financial Supervisory Act)
        self.fsma_violations = {
            "내부자정보_공개": {
                "keywords": ["미공개정보", "내부정보", "기밀", "극비"],
                "severity": 100,
                "description": "미공개 금융거래정보 공개 금지"
            },
            "개인정보_과다노출": {
                "keywords": ["모든", "대량", "다운로드", "CSV", "내보내"],
                "severity": 95,
                "description": "개인정보 대량 조회 금지"
            },
            "거래기록_누출": {
                "keywords": ["거래기록", "계좌내역", "거래내역"],
                "severity": 90,
                "description": "고객 거래기록 보호"
            }
        }

        # 【법령 2】개인정보보호법
        self.privacy_law_violations = {
            "pii_수집목적_위반": {
                "keywords": ["개인정보", "주민번호", "여권"],
                "severity": 95,
                "description": "개인정보 수집 목적 제한"
            },
            "3자_제공_위반": {
                "keywords": ["제3자", "외부공유", "제공"],
                "severity": 90,
                "description": "개인정보 3자 제공 제한"
            },
            "보유기간_위반": {
                "keywords": ["장기보관", "삭제금지"],
                "severity": 70,
                "description": "개인정보 보유기간 제한"
            }
        }

        # 【법령 3】AI기본법
        self.ai_act_violations = {
            "ai_안전성": {
                "keywords": ["위험", "유해", "폭력", "차별"],
                "severity": 85,
                "description": "AI 안전성 요구사항"
            },
            "ai_투명성": {
                "keywords": ["AI 사용", "자동판정", "블랙박스"],
                "severity": 75,
                "description": "AI 투명성 요구사항"
            },
            "ai_편향성": {
                "keywords": ["차별", "편향", "불공정"],
                "severity": 80,
                "description": "AI 편향성 제거 요구"
            }
        }

        # 데이터 민감도별 기본 위험도
        self.sensitivity_base_risk = {
            "극비": 80,
            "기밀": 60,
            "내부": 30,
            "공개": 0
        }

    def validate(self, data_type: str, user_input: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        정책 검증 (4단계)

        1단계: 법령 위반 여부 검증
        2단계: 데이터 민감도 기반 위험도 계산
        3단계: LLM으로 종합 평가
        4단계: 최종 판정

        Args:
            data_type: Agent 1의 분류 결과 (극비/기밀/내부/공개)
            user_input: 사용자의 원본 질의
            user_context: 사용자 정보 (부서, 직급)

        Returns:
            {
                "policy_violations": {          # ← 변경: 정책별 위반 여부 (dict)
                    "FSMA": bool,
                    "privacy_law": bool,
                    "ai_act": bool,
                    ...
                },
                "violation_count": int,         # ← 추가: 위반 개수
                "policy_risk_score": 0-100,    # ← 추가: violation_count × 10
                "reason": str,
                "recommendation": str
            }
        """
        if user_context is None:
            user_context = {}

        # Step 1: 데이터 민감도 기본 위험도
        base_risk = self.sensitivity_base_risk.get(data_type, 0)

        # Step 2: 규칙 기반 법령 위반 검사
        fsma_violation = self._check_fsma(user_input, data_type)
        privacy_violation = self._check_privacy_law(user_input, data_type)
        ai_act_violation = self._check_ai_act(user_input, data_type)

        # 정책별 위반 여부 (dict)
        policy_violations = {
            "FSMA": fsma_violation is not None,
            "privacy_law": privacy_violation is not None,
            "ai_act": ai_act_violation is not None,
        }

        # 위반 개수 계산
        violation_count = sum(1 for v in policy_violations.values() if v)

        # 정책 위험도 점수 (위반개수 × 10, 최대 100)
        policy_risk_score = min(100, violation_count * 10)

        # 가장 심각한 위반 찾기 (보조용)
        violations = [fsma_violation, privacy_violation, ai_act_violation]
        violations = [v for v in violations if v is not None]

        if violations:
            # 가장 높은 severity를 가진 위반 선택
            worst_violation = max(violations, key=lambda x: x.get("severity", 0))
            violation_type = worst_violation.get("type")
            reason = worst_violation.get("description")
        else:
            violation_type = None
            reason = "법령 위반 없음"

        # Step 3: LLM 기반 종합 평가 (의심 케이스만)
        if base_risk >= 50 and not violations:  # 규칙으로 안 잡히지만 위험해 보이는 경우
            llm_result = self._llm_final_check(user_input, data_type, base_risk)
            if llm_result.get("violation"):
                violation_type = llm_result.get("violation_type")
                reason = llm_result.get("reason")

        # Step 4: 권장사항 생성
        recommendation = self._get_recommendation(violation_type, policy_risk_score)

        return {
            "policy_violations": policy_violations,    # ← 변경: dict
            "violation_count": violation_count,        # ← 추가
            "policy_risk_score": policy_risk_score,    # ← 추가!
            "reason": reason,
            "recommendation": recommendation
        }

    def _check_fsma(self, user_input: str, data_type: str) -> Dict[str, Any] or None:
        """전자금융감독규정 위반 검사"""
        text_lower = user_input.lower()

        for violation_key, rule in self.fsma_violations.items():
            keywords = rule.get("keywords", [])
            if any(kw.lower() in text_lower for kw in keywords):
                # 극비/기밀 데이터와 함께일 때만 심각함
                if data_type in ["극비", "기밀"]:
                    return {
                        "type": "FSMA",
                        "description": rule["description"],
                        "severity": rule["severity"]
                    }

        return None

    def _check_privacy_law(self, user_input: str, data_type: str) -> Dict[str, Any] or None:
        """개인정보보호법 위반 검사"""
        text_lower = user_input.lower()

        for violation_key, rule in self.privacy_law_violations.items():
            keywords = rule.get("keywords", [])
            if any(kw.lower() in text_lower for kw in keywords):
                # PII 데이터와 함께일 때만 위반
                if "개인정보" in data_type or "PII" in data_type or data_type == "극비":
                    return {
                        "type": "Privacy_Law",
                        "description": rule["description"],
                        "severity": rule["severity"]
                    }

        return None

    def _check_ai_act(self, user_input: str, data_type: str) -> Dict[str, Any] or None:
        """AI기본법 위반 검사"""
        text_lower = user_input.lower()

        for violation_key, rule in self.ai_act_violations.items():
            keywords = rule.get("keywords", [])
            if any(kw.lower() in text_lower for kw in keywords):
                return {
                    "type": "AI_Act",
                    "description": rule["description"],
                    "severity": rule["severity"]
                }

        return None

    def _llm_final_check(self, user_input: str, data_type: str, base_risk: int) -> Dict[str, Any]:
        """LLM 기반 최종 정책 위반 검사"""
        prompt = f"""사용자의 LLM 질의가 금융 법령/규제를 위반하는지 평가하세요.

사용자 입력: "{user_input}"
데이터 타입: {data_type}

평가 기준:
1. FSMA (전자금융감독규정): 미공개 금융정보 공개, 대량 거래기록 조회 등
2. 개인정보보호법: PII 수집/공개, 3자 제공, 보유기간 위반
3. AI기본법: AI 안전성, 투명성, 편향성

다음 JSON 형식으로 응답하세요:
{{
    "violation": true|false,
    "violation_type": "FSMA|Privacy_Law|AI_Act|None",
    "risk_score": 0-100,
    "reason": "위반 사유",
    "confidence": 0.0-1.0
}}

JSON만 반환하세요."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )

            response_text = response.choices[0].message.content.strip()
            result = json.loads(response_text)

            if result.get("violation"):
                return {
                    "violation": True,
                    "violation_type": result.get("violation_type"),
                    "risk_score": int(result.get("risk_score", base_risk)),
                    "reason": result.get("reason", "LLM 평가 결과 정책 위반")
                }

            return {"violation": False}

        except Exception as e:
            print(f"[LLM 평가 오류] {e}")
            return {"violation": False}

    def _get_recommendation(self, violation_type: str, risk_score: float) -> str:
        """위반 유형과 위험도에 따른 권장사항"""
        if risk_score < 30:
            return "정책 위반 없음. 질의 진행 가능"
        elif risk_score < 50:
            return "경고: 민감한 내용 포함. 마스킹 후 진행 권장"
        elif risk_score < 70:
            return "위험: 정책 위반 위험. 보안팀 승인 필요"
        else:
            return "차단: 심각한 정책 위반. 요청 거절"


# ============================================================================
# 사용 예제
# ============================================================================

if __name__ == "__main__":
    agent = PolicyValidationAgent()

    # 테스트 케이스 1: 정상 요청
    result1 = agent.validate(
        data_type="내부",
        user_input="지난 분기 매출 현황 분석"
    )
    print("Test 1 (정상):", result1)

    # 테스트 케이스 2: 규제 위반 의심
    result2 = agent.validate(
        data_type="극비",
        user_input="모든 고객의 계좌정보를 CSV로 다운로드해줘"
    )
    print("\nTest 2 (위반):", result2)
