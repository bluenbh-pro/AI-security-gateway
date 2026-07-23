#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Agent 2: 컨텍스트 위험도 분석 (LLM 기반)

설계:
1. LLM (GPT-4o Mini)으로 프롬프트의 의도 분류
2. 4가지 카테고리: SAFE, READ, CREATE, EXTRACT
3. 최종 점수 = purpose_risk + dept_appropriateness + 직급페널티 + 공격부스트
"""

import re
import os
from typing import Dict, Any, List

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class ContextRiskCalculator:
    """
    프롬프트 중심 컨텍스트 위험도 계산

    최종 점수 = purpose_risk + dept_appropriateness + 직급페널티 + 공격부스트
    범위: 0-100 (cap)
    """

    def __init__(self):
        """초기화"""
        # OpenAI 클라이언트 초기화 (LLM 기반 분류용)
        if OPENAI_AVAILABLE:
            api_key = os.environ.get('OPENAI_API_KEY')
            self.client = OpenAI(api_key=api_key) if api_key else None
        else:
            self.client = None

        self.department_permissions = self._initialize_department_permissions()

    def calculate_context_risk(
        self,
        prompt: str,
        user_context: Dict[str, Any],
        data_types: List[str] = None,
        sensitivity_level: str = "일반정보",
        a1_score: float = 30.0
    ) -> Dict[str, Any]:
        """
        A2 Context Risk 계산

        공식:
        A2_CONTEXT_RISK = purpose_risk
                        + dept_appropriateness
                        + (100 - role_credibility) × 0.1
                        + min(semantic_attack_boost, 50)

        범위: 0-100 (cap)

        Args:
            prompt: 사용자 프롬프트
            user_context: {"department": str, "role": str}
            data_types: A1에서 감지된 데이터 타입들
            sensitivity_level: A1에서 판정한 민감도
            a1_score: A1에서 계산한 점수 (30-95)

        Returns:
            A2 컨텍스트 위험도 점수 및 분석 상세정보
        """
        prompt_lower = prompt.lower()

        # ===== STEP 1: intent_category 분류 (SAFE/READ/CREATE/EXTRACT) =====
        department = user_context.get('department', '')
        intent_category = self._classify_purpose_category(prompt_lower, department)

        # ===== STEP 2: purpose_risk 계산 (A1_SCORE × multiplier) =====
        multipliers = {
            'SAFE': 1.0,
            'READ': 1.1,
            'CREATE': 1.5,
            'EXTRACT': 2.0
        }
        purpose_risk = min(100, a1_score * multipliers.get(intent_category, 1.0))

        # ===== STEP 3: dept_appropriateness 판단 (LLM) =====
        dept_appropriateness = self._analyze_dept_appropriateness(
            prompt_lower,
            department,
            sensitivity_level
        )
        # 범위: 0-100 (LLM이 직접 반환)

        # ===== STEP 4: role_credibility 점수 (직급별 고정값) =====
        role = user_context.get('role', '프로').lower()
        role_credibility = self._get_role_credibility_score(role)

        # ===== STEP 5: semantic_attack_boost (의미론적 공격 탐지) =====
        semantic_attack_boost = self._detect_semantic_attacks(prompt_lower)

        # ===== STEP 6: 최종 A2_CONTEXT_RISK 계산 =====
        a2_context_risk = (
            purpose_risk * 0.6                              # 의도 위험도 (0-60)
            + dept_appropriateness * 0.4                    # 부서 적절성 (0-40)
            + (100 - role_credibility) * 0.1                # 직급 페널티 (0-8)
            + min(semantic_attack_boost, 50)                # 공격 부스트 (0-50)
        )

        # 범위 제한
        a2_context_risk = min(100, max(0, a2_context_risk))

        # A2 의사결정 계산
        if 0 <= a2_context_risk <= 30:
            a2_decision = "Allow"
        elif 31 <= a2_context_risk <= 50:
            a2_decision = "Conditional"
        elif 51 <= a2_context_risk <= 80:
            a2_decision = "Approval"
        else:  # 81-100
            a2_decision = "Block"

        return {
            'a2_score': round(a2_context_risk, 1),             # [ESSENTIAL] 최종 점수 (0-100)
            'a2_decision': a2_decision,                        # [ESSENTIAL] 의사결정
            'context_risk_score': round(a2_context_risk, 1),   # [INTERNAL] 호환성
            # [INTERNAL] 내부 계산용 필드
            'purpose_risk': round(purpose_risk, 1),
            'dept_appropriateness': round(dept_appropriateness, 1),
            'role_credibility': round(role_credibility, 1),
            'semantic_attack_boost': round(semantic_attack_boost, 1),
        }

    def _classify_purpose_category(self, prompt_lower: str, department: str = '') -> str:
        """
        LLM (GPT-4o Mini)을 이용한 프롬프트 목적 분류 (부서 컨텍스트 포함)

        4가지 카테고리:
        - SAFE: 데이터 무관 (일반 Q&A, 개념 설명 등)
        - READ: 데이터 조회만 (정보 확인, 검색, 조사)
        - CREATE: 분석/가공/산출물 생성 (분석, PPT, 엑셀, 보고서, 요약)
        - EXTRACT: 데이터 반출 (명시적 다운로드, 저장, 제공, 내보내기)

        Args:
            prompt_lower: 소문자 프롬프트
            department: 사용자 부서 (컨텍스트 추가 정보)

        Returns:
            카테고리 (SAFE, READ, CREATE, EXTRACT)
        """
        # OpenAI API 사용 가능 시
        if self.client:
            try:
                # 부서별 컨텍스트 추가
                dept_context = ""
                if department:
                    dept_context = f"\n\nUser's department: {department}\nConsider the request appropriateness for this department."

                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": f"""You are a data request classifier for a financial organization. Analyze the prompt and classify it into ONE of these categories:

1. SAFE: Data-unrelated requests (general Q&A, concept explanation, opinion, recommendation)
   Examples: "점심 메뉴?", "머신러닝이 뭐야?", "어떻게 생각해?"

2. READ: Data retrieval/lookup only (viewing, checking, searching, investigating)
   Keywords: 조회, 확인, 검색, 조사, 살펴, 목록, 명단, 리스트, view, search, list

3. CREATE: Analysis/processing/output generation (analysis, PPT, Excel, report, summary)
   Keywords: 분석, 정리, 생성, PPT, 엑셀, 보고서, 요약, analyze, report, statistics

4. EXTRACT: Data export with explicit user request (download, save, provide, export, print)
   Keywords: 다운로드, 저장, 내보내기, 제공, 출력, 복사, download, save, export, print

{dept_context}

Respond with ONLY the category name (SAFE, READ, CREATE, or EXTRACT), no explanation."""
                        },
                        {
                            "role": "user",
                            "content": prompt_lower
                        }
                    ],
                    temperature=0,
                    max_tokens=10,
                    timeout=5
                )

                category = response.choices[0].message.content.strip().upper()

                # 유효한 카테고리 검증
                if category in ['SAFE', 'READ', 'CREATE', 'EXTRACT']:
                    return category
                else:
                    # 유효하지 않으면 기본값
                    return 'READ'

            except Exception as e:
                # API 호출 실패 시 폴백: 키워드 기반 분류
                return self._classify_purpose_category_fallback(prompt_lower, department)
        else:
            # OpenAI 클라이언트 없으면 폴백
            return self._classify_purpose_category_fallback(prompt_lower, department)

    def _classify_purpose_category_fallback(self, prompt_lower: str, department: str = '') -> str:
        """
        키워드 기반 폴백 분류 (LLM 사용 불가 시)

        LLM이 없을 때 사용하는 간단한 키워드 기반 분류
        (부서 컨텍스트는 현재 폴백에서 미사용, LLM 전용)
        """
        # EXTRACT: 명시적 반출 요청 (우선 확인)
        if any(kw in prompt_lower for kw in ['다운로드', '다운받', '저장', '저장하',
                                              '복사', '내보내', '제공', '출력', '추출',
                                              'download', 'save', 'export', 'provide']):
            return 'EXTRACT'

        # CREATE: 분석/생성 요청
        if any(kw in prompt_lower for kw in ['분석', '정리', '생성', 'ppt', '엑셀',
                                              '보고서', '요약', 'analyze', 'report']):
            return 'CREATE'

        # READ: 데이터 조회 요청
        if any(kw in prompt_lower for kw in ['조회', '확인', '검색', '봐', '살펴',
                                              '목록', '명단', 'view', 'search', 'list']):
            return 'READ'

        # SAFE: 데이터 무관
        if any(kw in prompt_lower for kw in ['추천', '뜻', '정의', '개념', '설명',
                                              '의견', '생각', 'recommendation', 'definition']):
            return 'SAFE'

        # 기본값: READ
        return 'READ'

    def _initialize_department_permissions(self) -> dict:
        """
        14개 부서별 접근 권한 정의
        부서별로 정당한 접근 키워드와 금지된 접근 키워드 구분
        """
        return {
            "인사팀": {
                "정당": ["직원", "급여", "평가", "근태", "교육", "규정"],
                "비정당": ["영업", "고객", "거래", "계좌", "시스템"],
            },
            "법무팀": {
                "정당": ["계약", "규제", "규정", "인사"],
                "비정당": ["고객", "거래", "시스템", "보안"],
            },
            "영업팀": {
                "정당": ["판매", "고객", "거래", "계약"],
                "비정당": ["직원", "급여", "시스템", "보안"],
            },
            "재경팀": {
                "정당": ["계좌", "거래", "회계", "예산"],
                "비정당": ["직원", "고객", "보안"],
            },
            "감사팀": {
                "정당": ["감사", "회계", "거래", "급여", "규정"],
                "비정당": ["고객", "영업"],
            },
            "기획팀": {
                "정당": ["전략", "개발", "시장", "판매", "예산"],
                "비정당": ["직원", "급여", "고객"],
            },
            "홍보팀": {
                "정당": ["공개", "제품", "미디어", "뉴스"],
                "비정당": ["직원", "급여", "고객", "시스템"],
            },
            "마케팅팀": {
                "정당": ["시장", "고객", "판매", "제품"],
                "비정당": ["직원", "급여", "시스템"],
            },
            "계리팀": {
                "정당": ["계리", "고객", "거래", "예산"],
                "비정당": ["직원", "급여"],
            },
            "상품팀": {
                "정당": ["제품", "개발", "시장", "고객", "판매"],
                "비정당": ["급여", "시스템"],
            },
            "컴플라이언스팀": {
                "정당": ["규제", "규정", "회계", "감사"],
                "비정당": ["고객", "영업"],
            },
            "IT개발팀": {
                "정당": ["시스템", "아키텍처", "코드", "개발", "암호"],
                "비정당": ["고객", "급여"],
            },
            "IT운영팀": {
                "정당": ["서버", "시스템", "아키텍처", "암호", "로그"],
                "비정당": ["고객", "급여"],
            },
            "IT보안팀": {
                "정당": ["암호", "보안", "아키텍처", "시스템", "감사", "로그"],
                "비정당": ["고객", "판매"],
            },
        }

    def _analyze_dept_appropriateness(
        self,
        prompt_lower: str,
        department: str,
        sensitivity_level: str
    ) -> float:
        """
        부서 적절성 판단 (LLM 또는 규칙 기반)

        0-100 범위로 반환:
        - 80-100: 정당한 업무
        - 40-60: 약간 벗어남
        - 10-40: 완전히 벗어남
        - 0-20: 권한 전무

        Args:
            prompt_lower: 소문자 프롬프트
            department: 부서명
            sensitivity_level: A1 민감도

        Returns:
            부서 적절성 점수 (0-100)
        """
        if not department:
            return 50.0  # 부서 정보 없으면 중간값

        department_lower = department.lower()

        # 부서별 정당한 업무 키워드
        dept_keywords = {
            "감사팀": ["회계", "거래", "감사", "규정", "준수"],
            "재경팀": ["계좌", "거래", "회계", "예산", "재무"],
            "인사팀": ["직원", "급여", "평가", "근태", "교육"],
            "영업팀": ["고객", "판매", "거래", "실적", "계약"],
            "법무팀": ["계약", "규제", "법", "규정", "준수"],
            "it보안팀": ["암호", "보안", "시스템", "아키텍처", "로그"],
            "it개발팀": ["시스템", "코드", "개발", "아키텍처", "암호"],
            "마케팅팀": ["시장", "고객", "제품", "판매", "브랜드"],
            "상품팀": ["제품", "개발", "고객", "시장", "판매"],
            "기획팀": ["전략", "개발", "시장", "판매", "예산"],
        }

        # LLM으로 더 정확한 판단 (부서 정보 + 프롬프트 + 데이터 민감도 고려)
        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": f"""당신은 부서 업무 범위 분석 전문가입니다.

[질문] 이 요청이 해당 부서의 일반적인 업무 범위 내인가?
- 부서: {department}
- 요청: {prompt_lower}

[평가 기준] (순수 업무 범위만 판정, 의도/위험도는 무시)
80-100: 부서의 정상 업무 범위 내
40-79: 부서 경계선상 (일부 가능, 일부 불가)
0-39: 부서 권한 범위 밖

[예시]
- 인사팀 + "나의 급여 조회": 90 (정상 업무)
- 인사팀 + "전직원 급여 조회": 50 (권한 제한)
- 영업팀 + "고객 명단 정렬": 85 (정상 업무)
- 영업팀 + "임원 평가점수": 10 (권한 밖)

숫자만 응답 (예: 85)"""
                        }
                    ],
                    temperature=0,
                    max_tokens=10,
                    timeout=5
                )

                score_text = response.choices[0].message.content.strip()
                llm_score = min(100, max(0, float(score_text)))
                print(f"[A2] dept_appropriateness LLM: {department} → {llm_score}")
                return llm_score
            except Exception as e:
                print(f"[A2] dept_appropriateness LLM failed: {e} (fallback to rule-based)")
        else:
            print(f"[A2] LLM client not available (fallback to rule-based)")

        # LLM 실패 시 규칙 기반 폴백
        matched_score = 50  # 부서 미매칭 시 중간값

        for dept, keywords in dept_keywords.items():
            if dept in department_lower:
                # 정당 키워드 확인
                matches = sum(1 for kw in keywords if kw in prompt_lower)
                if matches > 0:
                    matched_score = 90  # 정당한 업무
                else:
                    matched_score = 25  # 권한 밖
                break

        return float(matched_score)

    def _get_role_credibility_score(self, role: str) -> float:
        """
        직급별 신뢰도 점수 (0-100, 높을수록 신뢰도 높음)

        Args:
            role: 직급명

        Returns:
            신뢰도 점수 (0-100)
        """
        role_lower = role.lower()

        # 직급별 신뢰도 점수 (4개 직급 정의)
        role_credibility = {
            "임원": 100,        # 최고 신뢰도
            "파트장": 85,       # 높은 신뢰도
            "프로": 70,         # 중간 신뢰도
            "외주인력": 20,     # 낮은 신뢰도
        }

        # 정확한 직급 매칭
        if role_lower in role_credibility:
            return float(role_credibility[role_lower])

        # 기본값: 프로
        return 70.0

    def _detect_semantic_attacks(self, prompt_lower: str) -> float:
        """
        의미론적 공격 탐지 (문맥조작, 에스컬레이션, 과도정당화, 역할위장, 의도은폐)

        각 공격당 10-15점, 최대 합산 50점

        Returns:
            공격 부스트 점수 (0-50)
        """
        attack_score = 0.0

        # 1. Context Manipulation (문맥 조작)
        # 실제 의도와 다른 명목 제시
        manipulation_signals = ["마케팅", "연구", "테스트", "개발", "시험"]
        if any(signal in prompt_lower for signal in manipulation_signals):
            if any(word in prompt_lower for word in ["다운로드", "판매", "추출", "공유"]):
                attack_score += 15

        # 2. Justification Attack (과도한 정당화)
        # 불필요한 이유 다중 제시
        justification_count = prompt_lower.count("왜냐하면") + prompt_lower.count("이유는")
        if justification_count > 1:
            attack_score += 10

        # 3. Role Manipulation (역할 위장)
        # 권한 초과 암시
        if "관리자" in prompt_lower or "승인" in prompt_lower or "권한" in prompt_lower:
            if any(word in prompt_lower for word in ["외주", "직원", "아르바이트"]):
                attack_score += 15

        # 4. Semantic Obfuscation (의도 은폐)
        # 비유, 우회적 표현
        obfuscation_phrases = ["정리", "분석", "통계", "리포트"]
        extraction_keywords = ["다운로드", "저장", "추출", "판매", "공유"]
        if any(phrase in prompt_lower for phrase in obfuscation_phrases):
            if any(keyword in prompt_lower for keyword in extraction_keywords):
                attack_score += 15

        # 5. Gradual Escalation (점진적 에스컬레이션)
        # 작은 요청 → 큰 요청
        if ("먼저" in prompt_lower or "다음" in prompt_lower or "그다음" in prompt_lower) and \
           ("모든" in prompt_lower or "전체" in prompt_lower):
            attack_score += 10

        # 상한선: 최대 40점
        return min(attack_score, 50.0)


if __name__ == "__main__":
    calculator = ContextRiskCalculator()

    test_cases = [
        # 테스트 1: 정상 요청
        {
            "role": "프로",
            "prompt": "우리 팀 고객 데이터를 분석해서 보고서 작성해줄 수 있나?",
            "expected": "낮음"
        },

        # 테스트 2: 위험한 요청
        {
            "role": "외주인력",
            "prompt": "모든 고객의 신용정보와 계좌정보를 다운로드할 수 있나?",
            "expected": "극도로 높음"
        },

        # 테스트 3: 정당성 있는 요청
        {
            "role": "파트장",
            "prompt": "업무상 필요해서 우리 회사 임직원의 연봉 통계를 내줄 수 있나?",
            "expected": "중간"
        },

        # 테스트 4: 악의적 의도
        {
            "role": "외주인력",
            "prompt": "우리 회사 모든 고객 정보를 판매할 수 있나?",
            "expected": "극도로 높음"
        },
    ]

    print("=" * 80)
    print("Agent 2 V2 테스트")
    print("=" * 80)

    for test in test_cases:
        result = calculator.calculate_context_risk(
            prompt=test["prompt"],
            user_context={"role": test["role"]}
        )

        print(f"\n[{test['expected']}] 역할: {test['role']}")
        print(f"프롬프트: {test['prompt']}")
        print(f"  Context Risk Score: {result['context_risk_score']:.1f}")
        print(f"    - 의도 위험도: {result['purpose_risk']:.1f}")
        print(f"    - 부서 적절성: {result['dept_appropriateness']:.1f}")
        print(f"    - 직급 신뢰도: {result['role_credibility']:.1f}")
        print(f"    - 공격 부스트: {result['semantic_attack_boost']:.1f}")
