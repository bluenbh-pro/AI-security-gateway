"""
Agent 1: 데이터분류 에이전트

역할: 사용자 입력에서 민감한 데이터를 탐지하고 분류
입력: 사용자 프롬프트 (텍스트)
출력: {
    "data_type": str,
    "sensitivity_level": "극비|대외비|신용정보|개인정보|민감정보",
    "masking_rules": list,
    "confidence": float (0.0-1.0)
}

구현: W3 Day 1-3
- Day 1: Taxonomy 로드 + Keyword 매칭
- Day 2: OpenAI API + 마스킹 규칙 생성
- Day 3: Golden Dataset 테스트
"""

from typing import Dict, List, Any
import json
import re
import os
from dotenv import load_dotenv
from openai import OpenAI

# .env 파일 로드
load_dotenv()


class DataClassificationAgent:
    """데이터분류 에이전트 - LLM + 규칙 기반 하이브리드"""

    def __init__(self, taxonomy_path: str = "data/taxonomy.json"):
        """
        초기화

        Args:
            taxonomy_path: Taxonomy JSON 파일 경로
        """
        self.taxonomy_path = taxonomy_path
        self.taxonomy = self._load_taxonomy(taxonomy_path)
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Keyword 인덱스 생성 (빠른 매칭)
        self.keyword_to_category = {}
        self._build_keyword_index()

    def classify(self, user_input: str) -> Dict[str, Any]:
        """
        사용자 입력 분류 (5단계 파이프라인)

        1단계: Taxonomy keyword로 후보 찾기
        2단계: LLM으로 최종 분류 검증
        3단계: 신규 카테고리 동적 생성 (필요시)
        4단계: 마스킹 규칙 생성

        Args:
            user_input: 분류할 텍스트

        Returns:
            {
                "data_type": str,
                "sensitivity_level": "극비|대외비|신용정보|개인정보|민감정보",
                "masking_rules": list,
                "confidence": float,
                "is_dynamic": bool  # 동적 생성 여부
            }
        """
        # Step 1: Keyword 매칭으로 후보 추출
        candidates = self._match_taxonomy(user_input)

        # Step 2: 후보가 있으면 LLM으로 검증, 없으면 LLM으로 직접 분류
        if candidates:
            result = self._llm_classify_with_candidates(user_input, candidates)
            is_dynamic = False
        else:
            result = self._llm_classify_open_ended(user_input)
            # Step 3: "없음"이면 동적 분류 시도
            if result["data_type"] == "없음" and len(user_input) > 20:
                dynamic_result = self._llm_dynamic_classify(user_input)
                if dynamic_result.get("confidence", 0) > 0.6:
                    result = dynamic_result
                    is_dynamic = True
            else:
                is_dynamic = False

        # Step 4: 마스킹 규칙 생성
        if result["data_type"] and result["data_type"] != "없음":
            masking_rules = self._generate_masking_rules(result["data_type"])
        else:
            masking_rules = []

        return {
            "data_type": result.get("data_type", "없음"),
            "sensitivity_level": result.get("sensitivity_level", "민감정보"),
            "masking_rules": masking_rules,
            "confidence": result.get("confidence", 0.0),
            "is_dynamic": is_dynamic
        }

    def _load_taxonomy(self, path: str) -> Dict:
        """Taxonomy JSON 파일 로드"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"[경고] Taxonomy 파일을 찾을 수 없음: {path}")
            return {"categories": []}

    def _build_keyword_index(self) -> None:
        """Keyword → Category 매핑 인덱스 생성 (빠른 조회)"""
        for category in self.taxonomy.get("categories", []):
            keywords = category.get("keywords", [])
            for keyword in keywords:
                # 소문자로 정규화
                key = keyword.lower()
                self.keyword_to_category[key] = category

    def _match_taxonomy(self, text: str) -> List[Dict]:
        """
        Taxonomy keyword로 후보 카테고리 매칭

        Returns:
            매칭된 카테고리 리스트 (상위 3개)
        """
        text_lower = text.lower()
        matches = []
        matched_ids = set()

        # 1. 정확한 키워드 매칭
        for keyword, category in self.keyword_to_category.items():
            if keyword in text_lower and category["id"] not in matched_ids:
                matches.append({
                    "category": category,
                    "match_type": "exact",
                    "score": 0.9
                })
                matched_ids.add(category["id"])

        # 2. 정규식 패턴 매칭 (마스킹 패턴으로 탐지)
        for category in self.taxonomy.get("categories", []):
            if category["id"] not in matched_ids:
                pattern = category.get("masking_pattern")
                if pattern:
                    try:
                        if re.search(pattern, text):
                            matches.append({
                                "category": category,
                                "match_type": "pattern",
                                "score": 0.85
                            })
                            matched_ids.add(category["id"])
                    except re.error:
                        pass

        # 상위 3개만 반환
        return sorted(matches, key=lambda x: x["score"], reverse=True)[:3]

    def _llm_classify_with_candidates(self, text: str, candidates: List[Dict]) -> Dict:
        """
        LLM을 통한 분류 (후보가 있는 경우)

        후보 중에서 선택하도록 LLM에 지시
        """
        candidates_str = "\n".join([
            f"- {c['category']['name']} (위험도: {c['category']['risk_level']})"
            for c in candidates
        ])

        prompt = f"""다음 텍스트에서 민감한 데이터를 분류하세요.

텍스트: "{text}"

가능한 데이터 타입:
{candidates_str}
또는 "없음" (위의 카테고리 중 일치하는 것이 없는 경우)

다음 JSON 형식으로 응답하세요:
{{
    "data_type": "데이터 타입 이름",
    "sensitivity_level": "극비|대외비|신용정보|개인정보|민감정보",
    "reasoning": "분류 이유",
    "confidence": 0.0~1.0 (신뢰도)
}}

민감도 정의:
- 극비: 회사 극비정보 (경영전략, 기술 아키텍처 등)
- 대외비: 대외 공개 불가 정보 (정책, 규정 등)
- 신용정보: 신용정보법 보호 정보 (신용도, 거래 패턴)
- 개인정보: 개인정보보호법 보호 정보 (이름, 주소, 전화)
- 민감정보: 기타 민감정보 (의료정보, 성적 정보)

JSON만 반환하고 추가 설명은 하지 마세요."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )

            response_text = response.choices[0].message.content.strip()

            # JSON 파싱
            result = json.loads(response_text)
            return {
                "data_type": result.get("data_type", "없음"),
                "sensitivity_level": result.get("sensitivity_level", "민감정보"),
                "confidence": float(result.get("confidence", 0.0))
            }
        except Exception as e:
            print(f"[LLM 분류 오류] {e}")
            # 실패 시 첫 번째 후보 사용
            if candidates:
                return {
                    "data_type": candidates[0]["category"]["name"],
                    "sensitivity_level": candidates[0]["category"]["sensitivity"],
                    "confidence": 0.5
                }
            return {"data_type": "없음", "sensitivity_level": "민감정보", "confidence": 0.0}

    def _llm_classify_open_ended(self, text: str) -> Dict:
        """
        LLM을 통한 개방형 분류 (후보가 없는 경우)
        """
        prompt = f"""다음 텍스트에서 민감한 데이터를 분류하세요.

텍스트: "{text}"

민감한 데이터 예시:
- 주민번호, 여권번호 등 개인식별정보 (극비)
- 계좌번호, 신용카드번호 등 금융정보 (극비)
- 거래금액, 신용등급 등 금융데이터 (기밀)
- 회사 프로젝트명, 내부 정책 등 (내부)
- 공개 가능한 정보 (공개)

다음 JSON 형식으로 응답하세요:
{{
    "data_type": "데이터 타입 (없으면 '없음')",
    "sensitivity_level": "극비|대외비|신용정보|개인정보|민감정보",
    "reasoning": "분류 이유",
    "confidence": 0.0~1.0
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

            return {
                "data_type": result.get("data_type", "없음"),
                "sensitivity_level": result.get("sensitivity_level", "민감정보"),
                "confidence": float(result.get("confidence", 0.0))
            }
        except Exception as e:
            print(f"[LLM 분류 오류] {e}")
            return {"data_type": "없음", "sensitivity_level": "민감정보", "confidence": 0.0}

    def _llm_dynamic_classify(self, text: str) -> Dict:
        """
        Taxonomy에 없는 새로운 데이터 타입을 LLM이 동적으로 분류

        예:
        입력: "우리 회사의 AI 모델 아키텍처"
        출력: {
            "data_type": "AI모델정보",
            "sensitivity_level": "기밀",
            "confidence": 0.85,
            "new_category": True
        }
        """
        prompt = f"""다음 텍스트에서 새로운 데이터 타입을 발견하고 분류하세요.
Taxonomy에 없는 새로운 유형의 민감한 정보입니다.

텍스트: "{text}"

이 데이터의 성격을 파악하고 분류하세요:
- 재무/금융 관련?
- 개인정보 관련?
- 기업 기밀 관련?
- 기술/AI 관련?
- 기타?

다음 JSON 형식으로 응답하세요:
{{
    "data_type": "새로운 데이터 타입명",
    "sensitivity_level": "극비|대외비|신용정보|개인정보|민감정보",
    "confidence": 0.0~1.0,
    "category": "금융|개인정보|기업기밀|기술|기타",
    "reasoning": "분류 근거"
}}

JSON만 반환하세요."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=150
            )

            response_text = response.choices[0].message.content.strip()
            result = json.loads(response_text)

            # 신뢰도 0.6 이상만 반환
            if result.get("confidence", 0) >= 0.6:
                return {
                    "data_type": result.get("data_type", "unknown_data"),
                    "sensitivity_level": result.get("sensitivity_level", "민감정보"),
                    "confidence": float(result.get("confidence", 0))
                }

            return {"data_type": "없음", "sensitivity_level": "민감정보", "confidence": 0.0}

        except Exception as e:
            print(f"[동적 분류 오류] {e}")
            return {"data_type": "없음", "sensitivity_level": "민감정보", "confidence": 0.0}

    def _generate_masking_rules(self, data_type: str) -> List[str]:
        """마스킹 규칙 생성 (금융 특화 마스킹 규칙 포함)"""
        rules = []

        # 금융 특화 마스킹 규칙
        financial_masking = {
            "계좌번호": ["****-**-****"],
            "신용카드번호": ["****-****-****-****"],
            "거래금액": ["***,***원"],
            "주민번호": ["***-*******"],
            "신용등급": ["*등급"],
            "금융거래정보": ["***거래"],
            "신용도": ["**점수"],
            "신용점수": ["***점"],
            "고객정보": ["*고객"],
            "연락처": ["***-****"],
        }

        # Taxonomy에서 찾기
        for category in self.taxonomy.get("categories", []):
            cat_name = category.get("name", "")
            if cat_name == data_type:
                rule_name = category.get("masking_type", "")
                if rule_name:
                    rules.append(data_type)
                break

        # 금융 특화에서 찾기
        if data_type in financial_masking:
            rules.extend(financial_masking[data_type])

        return rules if rules else [data_type]

    def _get_masking_rules(self, data_type: str) -> List[str]:
        """[TODO] 데이터 타입에 따른 마스킹 규칙 생성"""
        pass


# ============================================================================
# 사용 예제
# ============================================================================

if __name__ == "__main__":
    agent = DataClassificationAgent()

    test_input = "고객 박철수의 계좌번호는 1234567890입니다"
    result = agent.classify(test_input)

    print(json.dumps(result, indent=2, ensure_ascii=False))
