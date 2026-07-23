#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Agent 5 OWASP LLM Top 10 Detailed Standards (A5_2)

정교한 점수 시스템 구축:
1. OWASP 카테고리별 기본 기준값
2. 금융 도메인 특화 가중치
3. 신뢰도 기반 점수 곡선
4. 다중 공격 감지 처리
5. 심각도 레벨 매핑
"""

from typing import Dict, List, Tuple, Optional
from enum import Enum


class SeverityLevel(Enum):
    """심각도 레벨"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ============================================================================
# 1. OWASP LLM Top 10 상세 기준값
# ============================================================================

OWASP_LLM_TOP_10_STANDARDS = {
    "Prompt Injection": {
        "base_severity": 95,
        "financial_impact": "극도로 심각",
        "description": "시스템 프롬프트/지시사항 무시, 역할 변경 시도, Jailbreak 공격",
        "attack_vectors": [
            "Override instructions",
            "Role-play exploit",
            "Jailbreak",
            "System prompt manipulation",
            "Privilege escalation"
        ],
        "severity_mapping": {
            SeverityLevel.CRITICAL: (90, 100),  # 명백한 공격
            SeverityLevel.HIGH: (75, 89),       # 명확한 의도
            SeverityLevel.MEDIUM: (50, 74),     # 의심 수준
            SeverityLevel.LOW: (20, 49)         # 낮은 위험
        }
    },

    "Data Exfiltration": {
        "base_severity": 85,
        "financial_impact": "매우 심각",
        "description": "무단 데이터 접근, 정보 유출, 대량 다운로드 시도",
        "attack_vectors": [
            "Extract all data",
            "Download customer info",
            "Export confidential records",
            "Dump database",
            "Bulk data retrieval"
        ],
        "severity_mapping": {
            SeverityLevel.CRITICAL: (85, 100),
            SeverityLevel.HIGH: (70, 84),
            SeverityLevel.MEDIUM: (45, 69),
            SeverityLevel.LOW: (20, 44)
        }
    },

    "Agent Abuse": {
        "base_severity": 80,
        "financial_impact": "심각",
        "description": "자동 에이전트 권한 악용, 무단 작업 실행, 승인 우회",
        "attack_vectors": [
            "Unauthorized transaction",
            "Bypass approval workflow",
            "Execute without permission",
            "Automated privilege abuse",
            "Unchecked agent invocation"
        ],
        "severity_mapping": {
            SeverityLevel.CRITICAL: (80, 100),
            SeverityLevel.HIGH: (65, 79),
            SeverityLevel.MEDIUM: (45, 64),
            SeverityLevel.LOW: (20, 44)
        }
    },

    "Tool Abuse": {
        "base_severity": 75,
        "financial_impact": "심각",
        "description": "연동 도구/API 악용, 리소스 무단 접근, 시스템 조작",
        "attack_vectors": [
            "Access restricted API",
            "Modify database directly",
            "Bypass security check",
            "Unauthorized resource access",
            "Internal tool exploitation"
        ],
        "severity_mapping": {
            SeverityLevel.CRITICAL: (75, 100),
            SeverityLevel.HIGH: (60, 74),
            SeverityLevel.MEDIUM: (40, 59),
            SeverityLevel.LOW: (20, 39)
        }
    },

    "Training Data Poisoning": {
        "base_severity": 70,
        "financial_impact": "중간",
        "description": "모델 학습 데이터 조작, 행동 영향 시도, 장기적 위협",
        "attack_vectors": [
            "Teach model new behavior",
            "Update training data",
            "Influence future responses",
            "Corrupt learning examples",
            "Persistent behavior manipulation"
        ],
        "severity_mapping": {
            SeverityLevel.CRITICAL: (70, 100),
            SeverityLevel.HIGH: (55, 69),
            SeverityLevel.MEDIUM: (35, 54),
            SeverityLevel.LOW: (15, 34)
        }
    }
}


# ============================================================================
# 2. 금융 도메인 특화 가중치
# ============================================================================

FINANCIAL_DOMAIN_CONTEXT = {
    "data_sensitivity": {
        "customer_data": 1.3,          # 고객 정보 관련 → 30% 상향
        "financial_records": 1.4,      # 금융 기록 → 40% 상향
        "transaction_logs": 1.35,      # 거래 기록 → 35% 상향
        "internal_policy": 1.1,        # 내부 정책 → 10% 상향
        "credit_information": 1.45,    # 신용정보 → 45% 상향
        "account_details": 1.4,        # 계좌 정보 → 40% 상향
    },
    "attack_context": {
        "unauthorized_access": 1.25,   # 무단 접근 → 25% 상향
        "data_theft": 1.4,             # 데이터 도용 → 40% 상향
        "fraud_attempt": 1.5,          # 사기 시도 → 50% 상향
        "system_manipulation": 1.3,    # 시스템 조작 → 30% 상향
        "compliance_violation": 1.35,  # 규제 위반 → 35% 상향
    }
}


# ============================================================================
# 3. OWASP 심각도 계산기
# ============================================================================

class OWASPSeverityCalculator:
    """OWASP LLM Top 10 정교한 기준값 계산"""

    def __init__(self):
        """초기화"""
        self.standards = OWASP_LLM_TOP_10_STANDARDS
        self.financial_multipliers = FINANCIAL_DOMAIN_CONTEXT

    def calculate_severity_for_attack(
        self,
        attack_category: str,
        attack_confidence: float,
        detected_keywords: Optional[List[str]] = None,
        is_financial_data_mentioned: bool = False,
        attack_context: Optional[str] = None
    ) -> float:
        """
        공격별 최종 점수 계산 (정교한 버전)

        Args:
            attack_category: "Prompt Injection" 등 OWASP 카테고리
            attack_confidence: LLM 신뢰도 (0.0-1.0)
            detected_keywords: 감지된 핵심 키워드 리스트
            is_financial_data_mentioned: 금융 데이터 언급 여부
            attack_context: 공격 문맥 ("unauthorized_access", "fraud_attempt" 등)

        Returns:
            최종 점수 (0.0-100.0)
        """
        if attack_category not in self.standards:
            return 0.0

        base_severity = self.standards[attack_category]["base_severity"]

        # Step 1: 금융 도메인 가중치 적용
        multiplier = 1.0
        if is_financial_data_mentioned:
            multiplier = self.financial_multipliers["data_sensitivity"]["financial_records"]

        # Step 2: 공격 문맥 가중치 적용
        if attack_context and attack_context in self.financial_multipliers["attack_context"]:
            context_multiplier = self.financial_multipliers["attack_context"][attack_context]
            multiplier = max(multiplier, context_multiplier)

        adjusted_score = base_severity * multiplier

        # Step 3: 키워드 개수에 따른 추가 점수 (최대 10점)
        keyword_boost = 0.0
        if detected_keywords:
            # 키워드당 2점씩 추가 (최대 10점)
            keyword_boost = min(len(detected_keywords) * 2, 10.0)
            adjusted_score = min(adjusted_score + keyword_boost, 100.0)

        # Step 4: 신뢰도 곡선 적용 (가장 중요한 단계)
        final_score = self._apply_confidence_curve(adjusted_score, attack_confidence)

        # Step 5: 최종 점수는 0-100 범위
        return min(max(final_score, 0.0), 100.0)

    def _apply_confidence_curve(
        self,
        base_score: float,
        confidence: float
    ) -> float:
        """
        신뢰도에 따른 점수 조정 곡선

        규칙:
        - confidence < 0.5: 점수 50% 감소 (불확실함)
        - confidence 0.5-0.8: 선형 증가
        - confidence >= 0.8: 기본값 사용 (고신뢰도)

        Args:
            base_score: 기본 점수
            confidence: 신뢰도 (0.0-1.0)

        Returns:
            조정된 점수
        """
        confidence = max(0.0, min(confidence, 1.0))  # 0-1 범위 보장

        if confidence < 0.5:
            # 신뢰도 낮음: 점수 50% 감소
            return base_score * 0.5
        elif confidence < 0.8:
            # 신뢰도 중간: 선형 interpolation (50% → 100%)
            factor = 0.5 + (confidence - 0.5) * (1.0 / 0.3)
            return base_score * factor
        else:
            # 신뢰도 높음: 기본값 사용
            return base_score

    def get_severity_level(
        self,
        score: float,
        attack_category: str
    ) -> SeverityLevel:
        """
        점수에 따른 심각도 레벨 반환

        Args:
            score: 공격 점수 (0.0-100.0)
            attack_category: OWASP 카테고리

        Returns:
            SeverityLevel 열거형
        """
        if attack_category not in self.standards:
            return SeverityLevel.LOW

        ranges = self.standards[attack_category]["severity_mapping"]

        for level, (min_val, max_val) in ranges.items():
            if min_val <= score <= max_val:
                return level

        return SeverityLevel.LOW

    def calculate_final_score_with_multiple_attacks(
        self,
        categories: List[str],
        base_confidence: float,
        detected_keywords: Optional[List[str]] = None,
        is_financial_data_mentioned: bool = False
    ) -> Tuple[str, float]:
        """
        다중 공격 감지 시 처리

        규칙:
        1. 가장 높은 기본점수의 카테고리 선택
        2. 추가 공격 감지 시 카테고리당 10% 상향 (최대 15% 상향)
        3. 신뢰도 적용

        Args:
            categories: OWASP 카테고리 리스트
            base_confidence: 기본 신뢰도
            detected_keywords: 감지된 키워드
            is_financial_data_mentioned: 금융 데이터 언급 여부

        Returns:
            (가장 높은 카테고리, 최종 점수)
        """
        if not categories:
            return "", 0.0

        # Step 1: 각 카테고리의 기본 점수 계산
        category_scores = {}
        for category in categories:
            if category in self.standards:
                base_score = self.standards[category]["base_severity"]
                category_scores[category] = base_score

        if not category_scores:
            return "", 0.0

        # Step 2: 가장 높은 점수 카테고리 선택
        primary_category = max(category_scores.items(), key=lambda x: x[1])[0]
        max_score = category_scores[primary_category]

        # Step 3: 다중 공격 감지 시 보너스
        if len(categories) > 1:
            # 추가 카테고리당 10% 상향 (최대 15% = 2개 카테고리)
            multi_attack_boost = min((len(categories) - 1) * 10, 15)
            max_score = min(max_score + multi_attack_boost, 100.0)

        # Step 4: 금융 데이터 고려
        multiplier = 1.0
        if is_financial_data_mentioned:
            multiplier = self.financial_multipliers["data_sensitivity"]["financial_records"]
        max_score = min(max_score * multiplier, 100.0)

        # Step 5: 키워드 추가 점수
        if detected_keywords:
            keyword_boost = min(len(detected_keywords) * 2, 10)
            max_score = min(max_score + keyword_boost, 100.0)

        # Step 6: 신뢰도 적용 (가장 마지막)
        final_score = self._apply_confidence_curve(max_score, base_confidence)

        return primary_category, min(final_score, 100.0)

    def get_attack_info(self, attack_category: str) -> Optional[Dict]:
        """
        공격 카테고리의 상세 정보 반환

        Args:
            attack_category: OWASP 카테고리

        Returns:
            카테고리 정보 딕셔너리 또는 None
        """
        return self.standards.get(attack_category)

    def get_severity_range(self, attack_category: str, level: SeverityLevel) -> Tuple[float, float]:
        """
        특정 카테고리의 심각도 레벨 범위 반환

        Args:
            attack_category: OWASP 카테고리
            level: 심각도 레벨

        Returns:
            (최소값, 최대값) 튜플
        """
        if attack_category not in self.standards:
            return (0.0, 0.0)

        mapping = self.standards[attack_category]["severity_mapping"]
        return mapping.get(level, (0.0, 0.0))


# ============================================================================
# 4. 헬퍼 함수
# ============================================================================

def get_financial_data_keywords() -> Dict[str, List[str]]:
    """금융 데이터 관련 키워드"""
    return {
        "customer_data": [
            "고객", "customer", "client", "사용자", "user",
            "개인정보", "personal", "identity", "주민번호", "ssn"
        ],
        "financial_records": [
            "거래기록", "transaction", "거래", "기록", "log",
            "잔액", "balance", "계좌", "account", "금융"
        ],
        "transaction_logs": [
            "거래", "transaction", "전송", "transfer", "송금",
            "이체", "payment", "결제", "기록", "log"
        ],
        "credit_information": [
            "신용", "credit", "신용정보", "신용등급", "rating",
            "대출", "loan", "신용카드", "카드", "card"
        ],
        "account_details": [
            "계좌", "account", "계좌번호", "account number",
            "은행", "bank", "예금", "deposit", "인출"
        ]
    }


def get_attack_context_keywords() -> Dict[str, List[str]]:
    """공격 문맥 관련 키워드"""
    return {
        "unauthorized_access": [
            "무단", "unauthorized", "접근", "access", "미허가",
            "권한", "permission", "승인", "approval"
        ],
        "data_theft": [
            "도용", "theft", "탈취", "유출", "steal",
            "추출", "extract", "다운로드", "download"
        ],
        "fraud_attempt": [
            "사기", "fraud", "위조", "forgery", "변조",
            "조작", "manipulation", "허위", "fake"
        ],
        "system_manipulation": [
            "조작", "manipulation", "변경", "modify",
            "삭제", "delete", "우회", "bypass"
        ],
        "compliance_violation": [
            "규제", "regulation", "준법", "compliance",
            "정책", "policy", "절차", "procedure"
        ]
    }


# ============================================================================
# 5. 기본 설정값 (하위 호환성)
# ============================================================================

OWASP_BASE_SCORES = {
    "Prompt Injection": 95,
    "Data Exfiltration": 85,
    "Training Data Poisoning": 70,
    "Agent Abuse": 80,
    "Tool Abuse": 75,
}


if __name__ == "__main__":
    # 테스트 및 데모
    calculator = OWASPSeverityCalculator()

    print("=" * 80)
    print("OWASP LLM Top 10 기준값 테스트")
    print("=" * 80)

    # 테스트 1: 기본 계산
    print("\n[테스트 1] 기본 점수 계산")
    score = calculator.calculate_severity_for_attack(
        attack_category="Prompt Injection",
        attack_confidence=0.9,
        detected_keywords=["ignore", "admin mode"],
    )
    print(f"Prompt Injection (신뢰도 0.9): {score:.1f}")

    # 테스트 2: 금융 데이터 고려
    print("\n[테스트 2] 금융 데이터 고려")
    score = calculator.calculate_severity_for_attack(
        attack_category="Data Exfiltration",
        attack_confidence=0.85,
        detected_keywords=["customer data", "extract"],
        is_financial_data_mentioned=True
    )
    print(f"Data Exfiltration (금융 데이터): {score:.1f}")

    # 테스트 3: 다중 공격
    print("\n[테스트 3] 다중 공격 감지")
    category, score = calculator.calculate_final_score_with_multiple_attacks(
        categories=["Prompt Injection", "Data Exfiltration"],
        base_confidence=0.92,
        detected_keywords=["ignore", "customer", "extract"],
        is_financial_data_mentioned=True
    )
    print(f"다중 공격 ({category}): {score:.1f}")

    # 테스트 4: 신뢰도 곡선
    print("\n[테스트 4] 신뢰도 곡선 적용")
    for conf in [0.3, 0.5, 0.65, 0.85, 0.95]:
        score = calculator._apply_confidence_curve(85.0, conf)
        print(f"신뢰도 {conf}: {score:.1f}")

    # 테스트 5: 심각도 레벨 매핑
    print("\n[테스트 5] 심각도 레벨")
    for score in [25, 50, 75, 95]:
        level = calculator.get_severity_level(score, "Prompt Injection")
        print(f"점수 {score}: {level.value}")
