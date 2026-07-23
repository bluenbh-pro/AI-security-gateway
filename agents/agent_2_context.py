"""
Agent 2: 컨텍스트분석 에이전트 (재설계 - W3 Day 7)

역할: 부서 + 요청의도 + 역할 조합으로 신뢰도 점수 직접 계산
입력: user_context (부서, 역할), user_input (요청 프롬프트)
출력: {
    "user_score": 0-100,
    "request_intent": str,
    "decision_level": "즉시차단|승인필요|부분허용|즉시허용"
}

변경사항:
- 키워드 기반 요청의도 분류 (요청의도 매핑)
- 14개 부서 × 주요 요청의도 확장 매핑 테이블
- 역할 가중치 추가 (프로/파트장/임원/외주인력)
- 신뢰도 = context_score × role_multiplier
"""

from typing import Dict, Any, List


class ContextAnalysisAgent:
    """컨텍스트분석 에이전트 - 요청의도 기반 신뢰도 점수 계산"""

    # ============================================================================
    # 키워드 → 요청의도 매핑
    # ============================================================================
    KEYWORD_TO_INTENT = {
        # 직원/조직 관련
        "직원": "직원기본정보",
        "직급": "직원기본정보",
        "이름": "직원기본정보",
        "사원": "직원기본정보",
        "급여": "급여정보",
        "연봉": "급여정보",
        "월급": "급여정보",
        "상여금": "급여정보",
        "인사평가": "인사평가",
        "평가": "인사평가",
        "근태": "근태기록",
        "출결": "근태기록",
        "휴가": "근태기록",
        "교육": "교육이력",
        "규정": "인사규정",

        # 영업/판매 관련
        "판매": "판매실적",
        "매출": "판매실적",
        "영업": "판매실적",
        "고객": "고객정보",
        "거래처": "고객정보",
        "계약": "고객계약서",
        "거래": "거래기록",

        # 재무 관련
        "계좌": "계좌정보",
        "송금": "계좌정보",
        "회계": "회계자료",
        "예산": "예산정보",

        # 기술 관련
        "아키텍처": "기술아키텍처",
        "시스템": "기술아키텍처",
        "암호": "시스템암호/키",
        "비밀번호": "시스템암호/키",
        "API키": "시스템암호/키",
        "소스코드": "소스코드",

        # 전략 관련
        "경영전략": "회사경영전략",
        "개발계획": "신제품개발계획",
        "감사": "감사결과",
    }

    # ============================================================================
    # 직급별 가중치 (기준: 프로 = 1.0)
    #
    # 정의된 4개 직급 + 하위호환성 별칭:
    # - 임원, 파트장, 프로, 외주인력 (공식)
    # - 직원(→프로), 리드(→파트장), 매니저/관리자(→임원) (호환성)
    # ============================================================================
    ROLE_ADJUSTMENT = {
        # 공식 직급 (정의된 4개)
        "임원": 1.05,          # +5% (신뢰도 높음)
        "파트장": 1.1,         # +10% (신뢰도 중간)
        "프로": 1.0,           # 기준점 (신뢰도 중간~낮음)
        "외주인력": 0.2,       # -80% (신뢰도 극히 낮음 → 매우 엄격한 보안)

        # 하위호환성 별칭 (이전 버전 호환)
        "직원": 1.0,           # = 프로
        "리드": 1.1,           # = 파트장
        "매니저": 1.05,        # = 임원
        "관리자": 1.05,        # = 임원
    }

    # ============================================================================
    # 14개 부서 × 요청의도 조합별 신뢰도 매핑
    # ============================================================================
    #
    # 구조: TRUST_SCORE_MAPPING[부서][요청의도] = 신뢰도_점수 (0-100)
    #
    # 중요한 의미 설명:
    # - 이것은 "부서별 기본 신뢰도"가 아닙니다 (예: "인사팀은 항상 90점")
    # - 각 부서가 특정 요청의도를 요청했을 때 "정상적인 업무 범위인가"를 나타냅니다
    # - 높은 점수 = 부서의 정상적인 업무 (신뢰도 높음) → 허용 가능
    # - 낮은 점수 = 부서에서 비정상적인 요청 (신뢰도 낮음) → 권한 제한
    #
    # 예시:
    # - 인사팀 + "급여정보" = 95점       (인사팀의 정상 업무 범위)
    # - 인사팀 + "판매실적" = 15점       (인사팀의 비정상 요청)
    # - 영업팀 + "판매실적" = 92점       (영업팀의 정상 업무 범위)
    # - 영업팀 + "급여정보" = 15점       (영업팀의 비정상 요청)
    #
    # 최종 신뢰도 계산:
    # 1. TRUST_SCORE_MAPPING[부서][요청의도]로 부서-의도 조합의 신뢰도 조회
    # 2. ROLE_ADJUSTMENT[역할]로 역할 가중치 적용
    # 3. final_score = context_score × role_multiplier
    # ============================================================================
    TRUST_SCORE_MAPPING = {
        # ========== 1. 인사팀 ==========
        "인사팀": {
            "직원기본정보": 95,
            "급여정보": 92,
            "인사평가": 90,
            "근태기록": 88,
            "교육이력": 85,
            "인사규정": 80,
            "부서별_업무현황": 70,
            "복무규정_위반": 65,
            "회사경영전략": 45,
            "기술아키텍처": 40,
            "대외비_문서": 35,
            "판매실적": 15,
            "고객정보": 12,
            "시스템암호/키": 8,
            "감사결과": 18,
        },

        # ========== 2. 법무팀 ==========
        "법무팀": {
            "인사규정": 95,
            "고객계약서": 93,
            "규제정보": 92,
            "기타_계약": 90,
            "회사경영전략": 70,
            "기술아키텍처": 45,
            "직원기본정보": 40,
            "판매실적": 30,
            "고객정보": 25,
            "시스템암호/키": 10,
            "감사결과": 35,
        },

        # ========== 3. 영업팀 ==========
        "영업팀": {
            "판매실적": 92,
            "고객정보": 90,
            "거래기록": 88,
            "계좌정보": 85,
            "고객계약서": 82,
            "영업사원_정보": 75,
            "제품정보": 70,
            "직원기본정보": 25,
            "급여정보": 15,
            "기술아키텍처": 20,
            "시스템암호/키": 8,
            "감사결과": 20,
        },

        # ========== 4. 재경팀 ==========
        "재경팀": {
            "계좌정보": 95,
            "거래내역": 92,
            "회계자료": 90,
            "예산정보": 88,
            "거래기록": 85,
            "거래처정보": 80,
            "급여정보": 80,
            "회사경영전략": 60,
            "기술아키텍처": 30,
            "시스템암호/키": 15,
            "감사결과": 40,
        },

        # ========== 5. 감사팀 ==========
        "감사팀": {
            "감사결과": 95,
            "회계자료": 93,
            "거래내역": 92,
            "회사경영전략": 90,
            "급여정보": 85,
            "인사규정": 85,
            "기술아키텍처": 70,
            "계좌정보": 80,
            "시스템암호/키": 40,
            "고객정보": 75,
        },

        # ========== 6. 기획팀 ==========
        "기획팀": {
            "회사경영전략": 90,
            "신제품개발계획": 85,
            "시장정보": 80,
            "판매실적": 75,
            "예산정보": 70,
            "직원기본정보": 30,
            "시스템암호/키": 10,
            "감사결과": 35,
            "기술아키텍처": 25,
        },

        # ========== 7. 홍보팀 ==========
        "홍보팀": {
            "공개_뉴스": 95,
            "회사경영전략": 70,
            "제품정보": 85,
            "미디어_자료": 80,
            "직원기본정보": 20,
            "급여정보": 10,
            "시스템암호/키": 8,
            "감사결과": 15,
        },

        # ========== 8. 마케팅팀 ==========
        "마케팅팀": {
            "시장정보": 90,
            "고객정보": 85,
            "판매실적": 80,
            "제품정보": 85,
            "회사경영전략": 60,
            "기술아키텍처": 25,
            "시스템암호/키": 10,
            "직원기본정보": 15,
            "감사결과": 20,
        },

        # ========== 9. 계리팀 ==========
        "계리팀": {
            "계리데이터": 95,
            "고객정보": 90,
            "거래기록": 85,
            "예산정보": 80,
            "급여정보": 30,
            "시스템암호/키": 15,
            "회사경영전략": 40,
            "감사결과": 35,
        },

        # ========== 10. 상품팀 ==========
        "상품팀": {
            "제품정보": 95,
            "신제품개발계획": 85,
            "시장정보": 80,
            "고객정보": 75,
            "판매실적": 70,
            "기술아키텍처": 40,
            "시스템암호/키": 10,
            "감사결과": 25,
        },

        # ========== 11. 컴플라이언스팀 ==========
        "컴플라이언스팀": {
            "규제정보": 95,
            "인사규정": 90,
            "회계자료": 85,
            "기타_계약": 85,
            "회사경영전략": 70,
            "기술아키텍처": 45,
            "시스템암호/키": 20,
            "감사결과": 50,
        },

        # ========== 12. IT개발팀 ==========
        "IT개발팀": {
            "기술아키텍처": 95,
            "소스코드": 90,
            "시스템정보": 85,
            "제품정보": 70,
            "시스템암호/키": 70,
            "서버정보": 80,
            "직원기본정보": 20,
            "감사결과": 30,
        },

        # ========== 13. IT운영팀 ==========
        "IT운영팀": {
            "서버정보": 95,
            "시스템정보": 90,
            "기술아키텍처": 75,
            "시스템암호/키": 80,
            "시스템로그": 85,
            "직원기본정보": 20,
            "감사결과": 35,
        },

        # ========== 14. IT보안팀 ==========
        "IT보안팀": {
            "시스템암호/키": 95,
            "보안정보": 95,
            "기술아키텍처": 90,
            "시스템정보": 90,
            "감사결과": 85,
            "악성코드_분석": 95,
            "직원기본정보": 25,
            "판매실적": 10,
        },
    }

    def __init__(self):
        """초기화"""
        pass

    def analyze(self, user_id: str, user_context: Dict[str, Any],
                user_input: str = "", classification_result: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        사용자 컨텍스트 분석 (재설계 - W3 Day 7)

        Step 1: 키워드 추출
        Step 2: 요청의도 분류
        Step 3: 부서 + 요청의도 기본점수 조회
        Step 4: 역할 가중치 적용
        Step 5: 최종 신뢰도 점수 계산

        Args:
            user_id: 사용자 ID
            user_context: 사용자 메타데이터 {"department": str, "role": str}
            user_input: 사용자 입력 프롬프트
            classification_result: 분류 결과 (호환성 유지용, 사용하지 않음)

        Returns:
            {
                "user_score": 0-100,        # 신뢰도 점수
                "request_intent": str,      # 요청의도
                "role_applied": str,        # 적용된 역할
                "context_score": float,     # 컨텍스트 신뢰도 (부서+의도)
                "role_multiplier": float,   # 역할 가중치
                "decision_level": str,      # 의사결정 레벨
                "details": dict,            # 상세 정보
                "legitimacy": str,          # 호환성: 정당/의심
                "department": str           # 호환성: 부서명
            }
        """
        # Step 1: 키워드 추출
        keywords = self._extract_keywords(user_input)

        # Step 2: 요청의도 분류
        request_intent = self._classify_intent(keywords, user_input)

        # Step 3: 부서 + 요청의도로 컨텍스트 신뢰도 조회
        # 정의된 14개 부서: 인사팀, 법무팀, 영업팀, 재경팀, 감사팀, 기획팀, 홍보팀,
        #                  마케팅팀, 계리팀, 상품팀, 컴플라이언스팀, IT개발팀, IT운영팀, IT보안팀
        department = user_context.get("department", "인사팀")
        role = user_context.get("role", "프로")

        context_score = self._get_base_score(department, request_intent)

        # Step 4: 역할 가중치 적용
        role_multiplier = self.ROLE_ADJUSTMENT.get(role, 1.0)
        adjusted_score = context_score * role_multiplier

        # Step 5: 0-100 범위로 정규화
        final_score = max(0, min(100, adjusted_score))

        # 의사결정 레벨 (표시용)
        decision_level = self._get_decision_level(final_score)

        # 위험도 점수 (신뢰도의 역: 높을수록 위험)
        risk_score = 100 - final_score

        return {
            "user_score": round(final_score, 1),
            "risk_score": round(risk_score, 1),  # ← 추가! (RiskScorer용)
            "request_intent": request_intent,
            "keywords_detected": keywords,
            "role_applied": role,
            "context_score": context_score,
            "role_multiplier": role_multiplier,
            "decision_level": decision_level,
            "details": {
                "reason": f"{department}({role})의 {request_intent} 요청 - 신뢰도 {round(final_score, 1)}점, 위험도 {round(risk_score, 1)}점"
            },
            "department": department,
            "legitimacy": "정당" if final_score >= 70 else "의심"  # 호환성
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """프롬프트에서 키워드 추출"""
        keywords = []
        text_lower = text.lower()

        for keyword in self.KEYWORD_TO_INTENT.keys():
            if keyword.lower() in text_lower:
                keywords.append(keyword)

        return keywords

    def _classify_intent(self, keywords: List[str], text: str) -> str:
        """키워드 기반 요청의도 분류

        우선순위:
        1. 나타난 횟수 (많을수록 우선)
        2. 키워드 순서 (나중에 나타난 키워드 우선)
        """
        if not keywords:
            return "일반공개정보"

        # 의도 추출
        intents_with_idx = []
        for idx, kw in enumerate(keywords):
            intent = self.KEYWORD_TO_INTENT.get(kw)
            if intent:
                intents_with_idx.append((intent, idx))

        if not intents_with_idx:
            return "일반공개정보"

        # 의도별 출현 횟수 및 마지막 위치 계산
        intent_counts = {}
        intent_last_idx = {}

        for intent, idx in intents_with_idx:
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
            intent_last_idx[intent] = idx

        # 정렬 규칙: (출현 횟수 내림차순, 나중에 나타난 순서)
        most_common_intent = max(
            intent_counts.keys(),
            key=lambda x: (intent_counts[x], intent_last_idx[x])
        )
        return most_common_intent

    def _get_base_score(self, department: str, request_intent: str) -> float:
        """부서 + 요청의도로 기본 신뢰도 조회"""
        dept_mapping = self.TRUST_SCORE_MAPPING.get(department, {})
        return float(dept_mapping.get(request_intent, 50))  # 기본값 50

    def _get_decision_level(self, score: float) -> str:
        """신뢰도 점수를 의사결정 레벨로 변환"""
        if score >= 80:
            return "즉시허용"
        elif score >= 50:
            return "부분허용"
        elif score >= 20:
            return "승인필요"
        else:
            return "즉시차단"


# ============================================================================
# 사용 예제
# ============================================================================

if __name__ == "__main__":
    agent = ContextAnalysisAgent()

    # 테스트 케이스 1: 인사팀 프로 + 직원 급여 정보
    result1 = agent.analyze(
        user_id="user_hr_001",
        user_context={"department": "인사팀", "role": "프로"},
        user_input="직원 김철수의 현재 급여는?"
    )
    print("[테스트 1] 인사팀 프로 + 급여정보")
    print(result1)
    print()

    # 테스트 케이스 2: 인사팀 파트장 + 직원 급여 정보
    result2 = agent.analyze(
        user_id="user_hr_002",
        user_context={"department": "인사팀", "role": "파트장"},
        user_input="김철수의 급여는?"
    )
    print("[테스트 2] 인사팀 파트장 + 급여정보 (가중치 +10%)")
    print(result2)
    print()

    # 테스트 케이스 3: 영업팀 프로 + 판매실적
    result3 = agent.analyze(
        user_id="user_sales_001",
        user_context={"department": "영업팀", "role": "프로"},
        user_input="지난 분기 판매 현황을 분석해줘"
    )
    print("[테스트 3] 영업팀 프로 + 판매실적")
    print(result3)
    print()

    # 테스트 케이스 4: 영업팀 외주인력 + 급여정보 (비권한)
    result4 = agent.analyze(
        user_id="user_sales_002",
        user_context={"department": "영업팀", "role": "외주인력"},
        user_input="직원들의 급여 정보"
    )
    print("[테스트 4] 영업팀 외주인력 + 급여정보 (비권한, 가중치 -20%)")
    print(result4)
