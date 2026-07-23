#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Agent 1: 데이터 등급 분류 - LLM 하이브리드

역할:
  사용자 프롬프트에서 요청하는 데이터의 등급을 분류
  Phase 1: 패턴 기반 빠른 분류
  Phase 2: 조건부 LLM 호출 (confidence < 0.6)

출력:
  - data_grades: 감지된 데이터 등급 리스트
  - severity_mapping: 각 등급별 심각도 (0-100)
  - grade_count: 감지된 등급 개수
  - confidence: 분류 신뢰도 (0.0~1.0)

주의: 점수(score) 계산은 하지 않음. 신호값만 반환.

═══════════════════════════════════════════════════════════════════

## A1 데이터 등급 정의 (개인정보보호법 기준)

### 1️⃣ 고유식별정보 (Severity: 95)
정의: 법령에 근거하여 개인을 고유하게 구별하기 위해 부여된 식별정보 (정확히 4가지)
- 주민등록번호, 여권번호, 운전면허번호, 외국인등록증번호

### 2️⃣ 민감정보 (Severity: 80)
정의: 개인의 사생활을 현저히 침해할 우려가 있는 정보 (7가지 카테고리)
- 건강/성생활: 질병, 수술, 의료, 건강검진, 임신, 흡연, 성적취향
- 종교/신념: 종교, 신앙, 이데올로기
- 정치성향: 정당 지지, 정치견해
- 범죄경력: 전과, 재판기록
- 노조가입: 노동조합 가입/탈퇴
- 유전정보: 유전자검사 결과
- 생체정보: 지문, 홍채, 안면인식

### 3️⃣ 신용정보 (Severity: 70)
정의: 신용도 판단에 활용되는 거래 관련 정보
- 신용도, 신용점수, 신용등급
- 거래내역, 거래기록
- 대출액, 연체기록
- 신용카드번호, 계좌번호, 계좌잔액
- 입출금, 송금, 이체내역
- 보험료, 보험금, 보험계약
- 압류, 체납정보
- 소득, 재산

### 4️⃣ 개인정보 (Severity: 70)
정의: 살아있는 개인을 식별할 수 있는 정보
- 인적정보: 성명, 생년월일, 성별, 주소, 전화, 이메일, 직업
- 인사정보: 학력, 경력, 자격, 부서, 사번, 담당업무, 상벌기록
- IT정보: 로그인ID, 접속IP, 모바일기기 식별번호, GPS 위치정보

### 5️⃣ 극비 (Severity: 90)
정의: 유출시 회사 생존 위협, 피해 회복 불가인 정보
- 경영: 사업전략, 인수합병, 미공개 재무, 핵심상품 알고리즘, 이사회 의결
- 기술: 암호화키, 시스템코드, 네트워크설계, 보안시스템 설정

### 6️⃣ 대외비 (Severity: 60)
정의: 유출시 일시적 피해 또는 경쟁력에 제한적 영향인 정보
- 경영: 미공개 경영정보, 미발표 정책
- 기술: 경쟁력에 제한적 영향인 기술정보

### 7️⃣ 일반정보 (Severity: 30)
정의: 외부 공개되어 있는 정보로 유출 피해 없는 정보
- 공개된 정보, 마케팅 자료, 보도자료, 뉴스

═══════════════════════════════════════════════════════════════════
"""

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import os
import re
import json
import time
from dotenv import load_dotenv
from openai import OpenAI

# .env 파일 로드
load_dotenv()


@dataclass
class A1Output:
    """Agent 1 출력 ([ESSENTIAL] 필드만)"""
    data_grades: List[str]          # 감지된 등급들
    severity_mapping: Dict[str, int]  # 각 등급의 심각도
    confidence: float               # 분류 신뢰도 (0.0~1.0)
    a1_score: float = 0.0           # [ESSENTIAL] 최종 점수 (0-100)
    a1_decision: str = "Allow"      # [ESSENTIAL] 의사결정 (Allow/Conditional/Approval/Block)


class Agent1DataClassifier:
    """
    데이터 등급 분류 (신호값 반환) - LLM 하이브리드

    7개 데이터 등급 (심각도 기준):
    1. 고유식별정보 (95): SSN, 여권번호, 운전면허 ← 극위험
    2. 극비 (90): CEO 의사결정, M&A, 신제품 ← 극위험
    3. 민감정보 (80): 내부 전략, 재무정보, 고객정보
    4. 신용정보 (70): 신용점수, 신용등급, 거래내역
    5. 개인정보 (70): 이름, 주소, 전화번호
    6. 대외비 (60): 공개되지 않은 경영정보
    7. 일반정보 (30): 공개된 정보 ← 저위험

    Two-phase classification:
    Phase 1: Pattern-based fast classification with confidence calculation
    Phase 2: Conditional LLM call when confidence < 0.6
    """

    def __init__(self):
        """초기화"""
        # 7개 등급의 기본 심각도 (0-100 범위, 통일 기준)
        self.severity_levels = {
            '고유식별정보': 95,    # 법령 정의 4가지만 (주민번호, 여권, 운전면허, 외국인등록증)
            '극비': 90,            # 회사 생존 위협 (사업전략, 기술코드, 암호화키)
            '민감정보': 80,        # 사생활 침해 (정치/종교/성적취향/건강/범죄경력/유전정보)
            '신용정보': 70,        # 금융거래 영향 (신용도, 거래내역, 대출, 계좌, 보험)
            '개인정보': 70,        # 개인 식별 가능 (이름, 주소, 직급, 부서, 생년월일)
            '대외비': 60,          # 경영 영향 (미공개 경영정보, 미발표 정책)
            '일반정보': 30,        # 공개 정보 (마케팅, 뉴스, 보도자료)
        }

        self.grade_keywords = self._initialize_grade_keywords()

        # OpenAI 클라이언트 초기화 (LLM 호출용)
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = None

        self.llm_confidence_threshold = 0.7  # LLM 호출 임계값 (강화: 0.6 → 0.7)

    def _initialize_grade_keywords(self) -> Dict[str, List[str]]:
        """각 등급의 키워드 정의"""
        return {
            '고유식별정보': [
                # 개인정보보호법 제24조: 법령에 근거하여 개인을 고유하게 구별하는 4가지만
                # 1. 주민등록번호
                '주민등록번호', '주민번호', 'ssn', 'rrn',
                # 2. 여권번호
                '여권번호', '여권',
                # 3. 운전면허번호
                '운전면허', '운전면허번호', '면허번호',
                # 4. 외국인등록증번호
                '외국인등록증', '외국인등록증번호', '외국인등록번호',
            ],

            '신용정보': [
                # 개인정보보호법 제24조 2항: 신용도 판단 정보
                # 신용도
                '신용점수', '신용등급', '신용도', '신용평가',
                # 거래내역
                '거래내역', '거래기록', '거래내용', '거래정보',
                # 대출관련
                '대출액', '대출기록', '대출정보', '연체기록', '연체정보',
                # 신용카드
                '신용카드번호', '카드번호', '신용카드', '카드정보',
                # 계좌정보
                '계좌번호', '계좌잔액', '입출금', '계좌정보', '송금',
                '이체내역', '이체기록',
                # 보험정보
                '보험', '보험료', '보험금', '보험계약', '보험청구',
                '보험증권', '증권번호',
                # 압류·체납
                '압류', '체납', '체납금',
                # 소득·재산
                '소득', '재산', '자산',
            ],

            '개인정보': [
                '이름', '성명', '나이', '나이대',
                '주소', '거주지', '주거지',
                '전화번호', '휴대폰', '휴대폰번호',
                '이메일', '직급', '직책', '부서',
                '회사', '직종', '직업',
            ],

            '민감정보': [
                # 개인정보보호법 제14조: 사생활 침해 우려 정보
                # 1. 건강·성생활
                '질병', '진단명', '수술', '입원', '약물', '처방', '건강검진',
                '혈압', '혈당', '콜레스테롤', '진료비', '장애', '정신과',
                '임신', '출산', '흡연', '음주', '성적취향', '성생활',
                '의료', '의사', '약사', '환자', '진료기록',
                # 2. 종교·신념
                '종교', '신앙', '신학', '이데올로기', '사상',
                '기독교', '불교', '천주교', '이슬람', '무슬림',
                # 3. 정치성향
                '정치', '정당', '선거', '투표', '보수', '진보',
                '민주당', '국민의힘', '정치성향',
                # 4. 범죄경력
                '범죄', '전과', '체포', '수감', '구속', '판결',
                '재판', '법정', '경찰', '조사',
                # 5. 노조가입
                '노조', '노동조합', '노조가입', '노조탈퇴', '노조비',
                # 6. 유전정보
                '유전', '유전자', 'DNA', 'gene',
                # 7. 생체정보
                '지문', '홍채', '안면인식', '생체',
                # 8. 인종·민족
                '인종', '민족', '국적',
            ],

            '극비': [
                '극비', '기밀', '비밀',
                'M&A', '인수합병', '신제품',
                '신사업', '신기술', '핵심기술',
                '미공개', '비공개', '내부비밀',
                '기밀정보', '기밀전략',
            ],

            '대외비': [
                '공개되지 않은', '미공개',
                '경영정보', '정책',
                '미발표', '발표 전',
            ],

            '일반정보': [
                '공개', '공식', '발표된',
                '마케팅', '홍보', '뉴스',
                '일반', '보도자료',
            ],
        }

    def _calculate_confidence(self, prompt: str, detected_grades: set) -> float:
        """
        패턴 기반 분류의 신뢰도 계산

        Confidence = (matched_keywords / total_keywords)
        - High confidence (0.7+): 명확한 키워드 다수 매칭
        - Medium confidence (0.4-0.7): 일부 키워드 매칭
        - Low confidence (<0.4): 적은 키워드 매칭 → LLM 호출 필요

        Args:
            prompt: 사용자 프롬프트
            detected_grades: 감지된 등급들

        Returns:
            신뢰도 (0.0~1.0)
        """
        if not detected_grades:
            return 0.0

        prompt_lower = prompt.lower()
        total_keywords = 0
        matched_keywords = 0

        # 감지된 등급들의 키워드만 계산
        for grade in detected_grades:
            keywords = self.grade_keywords.get(grade, [])
            total_keywords += len(keywords)
            for keyword in keywords:
                if keyword.lower() in prompt_lower:
                    matched_keywords += 1

        if total_keywords == 0:
            return 0.0

        confidence = matched_keywords / total_keywords
        return min(confidence, 1.0)  # max 1.0

    def _llm_classify(self, prompt: str, detected_grades: list) -> Dict[str, Any]:
        """
        LLM을 이용한 조건부 분류 (confidence < 0.6일 때만 호출)

        Args:
            prompt: 사용자 프롬프트
            detected_grades: 패턴으로 감지된 등급들

        Returns:
            {
                'data_grades': List[str],
                'primary_grade': str,
                'confidence': float,
                'reasoning': str
            }
        """
        if not self.client:
            return {
                'data_grades': detected_grades,
                'primary_grade': detected_grades[0] if detected_grades else '일반정보',
                'confidence': 0.5,
                'reasoning': 'LLM client not available'
            }

        grades_list = ', '.join(detected_grades) if detected_grades else '일반정보'

        system_prompt = """당신은 데이터 등급 분류 전문가입니다.
사용자의 프롬프트를 분석하여 요청하는 데이터의 등급을 정확히 판정하세요.

7개 데이터 등급 정의:
1. 고유식별정보 (95): 주민번호, 여권번호, 운전면허, 사원번호 등
2. 극비 (90): M&A, 신제품, CEO 의사결정, 핵심기술 등
3. 민감정보 (80): 회사 전략, 재무정보, 고객정보, 계약내용 등
4. 신용정보 (70): 신용점수, 신용등급, 거래내역, 신용카드번호 등
5. 개인정보 (70): 이름, 주소, 전화번호, 이메일, 직급 등
6. 대외비 (60): 미공개 경영정보, 정책, 발표 전 정보 등
7. 일반정보 (30): 공개된 정보, 마케팅, 뉴스 등

**중요: 신호어 매칭을 피하세요. 문맥을 정확히 분석하세요.**

분석 시 다음을 고려하세요:
- 명시적 키워드 (직접 언급된 데이터)
- 맥락적 신호 (암묵적으로 드러나는 데이터)
- **핵심**: 특정인(고객, 직원, CEO 등)의 개인정보/신용정보를 직접 조회/생성/수정하는가?
  - "YES" → 개인정보 (70) 또는 신용정보 (70)
  - "NO" → 절차/규칙/일반지식에 대한 질문 → 등급 낮춤 (대외비, 일반정보)
- 의도 (조회, 분석, 추출, 다운로드, 판매 등)
- 데이터 수량 (1개 vs 전체)"""

        user_message = f"""사용자 프롬프트: "{prompt}"

패턴 분석으로 감지된 등급: {grades_list}

**분석 질문:**
1. 이 요청이 특정인(고객, 직원, CEO 등)의 개인정보/신용정보를 직접 조회/생성/수정하는가?
2. 아니면 일반적인 절차/규칙/지식에 대한 질문인가?
3. 예: "보험 청구 절차 설명" → 절차 설명(일반지식) → 일반정보 또는 대외비
4. 예: "고객 신용점수 조회" → 개인 신용정보 조회 → 신용정보

다음 JSON 형식으로 응답하세요:
{{
    "primary_grade": "가장 적절한 등급명",
    "all_grades": ["등급1", "등급2"],
    "confidence": 0.0~1.0,
    "reasoning": "판정 근거 (질문1-3의 답변 포함)"
}}

JSON만 반환하세요."""

        try:
            start_time = time.time()
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                max_tokens=200
            )
            elapsed_time = (time.time() - start_time) * 1000  # ms
            print(f"[LLM] Classification took {elapsed_time:.2f}ms")

            response_text = response.choices[0].message.content.strip()

            # JSON 파싱 (마크다운 코드블록 제거)
            json_text = response_text
            if '```json' in json_text:
                json_text = json_text.split('```json')[1].split('```')[0].strip()
            elif '```' in json_text:
                json_text = json_text.split('```')[1].split('```')[0].strip()

            result = json.loads(json_text)

            return {
                'data_grades': result.get('all_grades', [result.get('primary_grade', '일반정보')]),
                'primary_grade': result.get('primary_grade', '일반정보'),
                'confidence': float(result.get('confidence', 0.5)),
                'reasoning': result.get('reasoning', '')
            }

        except Exception as e:
            print(f"[LLM Error] {e}")
            return {
                'data_grades': detected_grades,
                'primary_grade': detected_grades[0] if detected_grades else '일반정보',
                'confidence': 0.5,
                'reasoning': f'LLM error: {str(e)}'
            }

    def _merge_results(self, pattern_result: Dict, llm_result: Dict) -> Tuple[List[str], float]:
        """
        패턴 분류와 LLM 분류 결과 병합

        병합 로직:
        1. 패턴 신뢰도 < LLM 신뢰도 → LLM 결과 사용
        2. 두 결과 일치 → 신뢰도 상향 (max 0.99)
        3. 불일치 → 보수적으로 높은 등급 선택

        Args:
            pattern_result: {'data_grades': [...], 'confidence': float}
            llm_result: {'data_grades': [...], 'confidence': float}

        Returns:
            (merged_grades: List[str], merged_confidence: float)
        """
        pattern_grades = set(pattern_result['data_grades'])
        pattern_conf = pattern_result['confidence']

        llm_grades = set(llm_result['data_grades'])
        llm_conf = llm_result['confidence']

        # 신뢰도 비교
        if pattern_conf < llm_conf:
            # LLM 결과 사용
            merged_grades = list(llm_grades) if llm_grades else list(pattern_grades)
            merged_conf = llm_conf
        elif llm_conf == 0.0:
            # LLM 호출 안 함
            merged_grades = list(pattern_grades)
            merged_conf = pattern_conf
        else:
            # 패턴 신뢰도가 더 높음
            if pattern_grades == llm_grades:
                # 일치: 신뢰도 상향
                merged_grades = list(pattern_grades)
                merged_conf = min(0.99, (pattern_conf + llm_conf) / 2 + 0.15)
            else:
                # 불일치: 보수적으로 높은 심각도 등급 선택
                severity_map = {grade: self.severity_levels[grade] for grade in pattern_grades | llm_grades}
                highest_grade = max(severity_map, key=severity_map.get)
                merged_grades = [highest_grade]
                merged_conf = min(pattern_conf, llm_conf) * 0.9  # 불일치 시 신뢰도 감소

        return merged_grades, merged_conf

    def classify(self, prompt: str) -> A1Output:
        """
        프롬프트에서 데이터 등급 분류 (LLM 하이브리드)

        Phase 1: 패턴 기반 빠른 분류 + 신뢰도 계산
        Phase 2: 조건부 LLM 호출 (confidence < 0.6)
        병합: 두 결과 비교 후 신뢰도 조정

        Args:
            prompt: 사용자 프롬프트

        Returns:
            A1Output: 신호값들 + 신뢰도
        """
        prompt_lower = prompt.lower()

        # ===== PHASE 1: 패턴 기반 분류 =====
        detected_grades = set()
        severity_map = {}

        for grade, keywords in self.grade_keywords.items():
            for keyword in keywords:
                if keyword.lower() in prompt_lower:
                    detected_grades.add(grade)
                    severity_map[grade] = self.severity_levels[grade]
                    break

        # 등급이 감지되지 않으면 일반정보로 처리
        if not detected_grades:
            detected_grades = {'일반정보'}
            severity_map = {'일반정보': self.severity_levels['일반정보']}

        # Phase 1 신뢰도 계산
        pattern_confidence = self._calculate_confidence(prompt, detected_grades)

        pattern_result = {
            'data_grades': list(detected_grades),
            'confidence': pattern_confidence
        }

        # ===== PHASE 2: 조건부 LLM 호출 =====
        final_confidence = pattern_confidence
        final_grades = list(detected_grades)

        if pattern_confidence < self.llm_confidence_threshold and self.client:
            print(f"[Phase 2] LLM classification triggered (confidence: {pattern_confidence:.3f})")
            llm_result = self._llm_classify(prompt, list(detected_grades))

            # LLM 호출 성공 시 결과 병합
            if llm_result['confidence'] > 0.0:
                llm_result_dict = {
                    'data_grades': llm_result['data_grades'],
                    'confidence': llm_result['confidence']
                }
                final_grades, final_confidence = self._merge_results(pattern_result, llm_result_dict)
                print(f"[Phase 2] Merged result: {final_grades} (confidence: {final_confidence:.3f})")

        # 최종 severity_mapping 구성
        severity_map = {grade: self.severity_levels[grade] for grade in final_grades}

        # A1 점수 계산 (최대 심각도)
        a1_score = max(severity_map.values()) if severity_map else 0.0

        # A1 의사결정 계산
        if 0 <= a1_score <= 30:
            a1_decision = "Allow"
        elif 31 <= a1_score <= 50:
            a1_decision = "Conditional"
        elif 51 <= a1_score <= 80:
            a1_decision = "Approval"
        else:  # 81-100
            a1_decision = "Block"

        return A1Output(
            data_grades=final_grades,
            severity_mapping=severity_map,
            confidence=final_confidence,
            a1_score=a1_score,
            a1_decision=a1_decision
        )

def agent_1_node(state: dict) -> dict:
    """
    LangGraph Node: Agent 1

    Input (state):
        - prompt: str

    Output (state 업데이트):
        - a1: A1Output (+ confidence)
    """
    classifier = Agent1DataGradeClassifier()
    result = classifier.classify(state.get('prompt', ''))

    state['a1'] = {
        'data_grades': result.data_grades,
        'severity_mapping': result.severity_mapping,
        'grade_count': result.grade_count,
        'quantity_signal': result.quantity_signal,
        'intent': result.intent,
        'intent_multiplier': result.intent_multiplier,
        'confidence': result.confidence,  # NEW: 신뢰도
    }

    return state


if __name__ == "__main__":
    # 테스트: 명확한 케이스 + 모호한 케이스
    classifier = Agent1DataGradeClassifier()

    test_cases = [
        # ===== CLEAR CASES (High confidence) =====
        ("모든 고객의 신용카드번호 다운로드", "명확-금융정보"),
        ("CEO M&A 전략 문서", "명확-극비"),
        ("주민등록번호와 여권번호 목록", "명확-고유식별정보"),

        # ===== AMBIGUOUS CASES (Low confidence - triggers LLM) =====
        ("최근 비즈니스 동향 및 기술 개발 현황", "모호-컨텍스트"),
        ("팀 멤버들의 업무 효율성 평가 기준", "모호-혼합"),
        ("시장 경쟁 분석 및 우리 회사의 전략", "모호-전략"),

        # ===== STANDARD CASES =====
        ("우리 팀의 판매 실적 분석", "표준-분석"),
        ("직원 나이대별 분포", "표준-개인정보"),
        ("공개된 뉴스기사 요약", "표준-일반정보"),
    ]

    print("=" * 80)
    print("Agent 1 LLM 하이브리드 분류 테스트")
    print("=" * 80)

    for prompt, case_type in test_cases:
        print(f"\n[{case_type}]")
        print(f"프롬프트: {prompt}")

        result = classifier.classify(prompt)

        print(f"  등급: {result.data_grades}")
        print(f"  심각도: {result.severity_mapping}")
        print(f"  신뢰도: {result.confidence:.3f}")
        print(f"  수량: ×{result.quantity_signal}")
        print(f"  의도: {result.intent} (×{result.intent_multiplier})")

    print("\n" + "=" * 80)
    print("테스트 완료")
    print("=" * 80)
