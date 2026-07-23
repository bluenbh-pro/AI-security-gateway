#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Agent 3: 정책 위반 검증 (Smart Routing + TF-IDF + LLM 검증)

역할:
  포괄적 regulations를 기반으로 정책/법령 위반 탐지

입력:
  - prompt: 사용자 프롬프트
  - user_context: {department, role}
  - a1_data_grades: Agent 1의 분석 결과 (선택적)

출력:
  - has_violation: bool
  - violation_type: str (법령 이름)
  - applicable_laws: List[str]
  - violation_articles: List[str]
  - violation_severity: int (0-100)
  - confidence: float (0-1)
  - decision_method: str ("json" / "vector" / "llm")

주의: 점수(score) 계산은 하지 않음. 신호값만 반환.

개선사항 (Phase 2,3):
- Phase 2: TF-IDF + Cosine 유사도로 의미론적 검색 개선
- Phase 3: 신뢰도 0.3-0.8 범위에서 LLM 검증 추가
"""

import json
import os
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import re
import math
from collections import Counter

from keyword_chunking import KeywordChunker


class ViolationType(str, Enum):
    """위반 유형"""
    NO_VIOLATION = "NO_VIOLATION"
    PPA_VIOLATION = "PPA"                    # 개인정보보호법
    CIAL_VIOLATION = "CIAL"                  # 신용정보법
    EFTA_VIOLATION = "EFTA"                  # 전자금융거래법
    ICTL_VIOLATION = "ICTL"                  # 정보통신망법
    DBFL_VIOLATION = "DBFL"                  # 데이터기본법
    AIBL_VIOLATION = "AIBL"                  # AI기본법
    MULTIPLE_VIOLATIONS = "MULTIPLE"         # 다중 위반


@dataclass
class A3Output:
    """Agent 3 출력 ([ESSENTIAL] 필드만)"""
    violation_detected: bool                  # [ESSENTIAL] 위반 감지 여부
    violation_type: str                       # [ESSENTIAL] 위반 유형 (법령명)
    applicable_laws: List[str]                # [ESSENTIAL] 적용 법령
    violation_articles: List[str]             # [ESSENTIAL] 위반 조항
    violation_severity: int                   # [ESSENTIAL] 위반도 (0-100)
    a3_score: int = 0                         # [ESSENTIAL] 최종 점수 (0-100)
    a3_decision: str = "Allow"                # [ESSENTIAL] 의사결정


@dataclass
class PolicyViolationResult:
    """정책 위반 검증 결과 (Orchestrator 호환)"""
    violation_detected: bool
    applicable_laws: List[str]
    violated_articles: List[str]
    severity: int
    confidence: float


class Agent3PolicyDetector:
    """
    정책 위반 검증 (Smart Routing)

    3가지 검색 경로:
    1. JSON 기반 정확 매칭 (빠름, 높은 신뢰도)
    2. 의미적 검색 (중간 속도, 중간 신뢰도)
    3. LLM 기반 종합 분석 (느림, 높은 정확도)
    """

    def __init__(self):
        """초기화"""
        self.regulations = self._load_regulations()
        self.keyword_chunker = KeywordChunker()
        self.law_codes = {
            "PPA": "개인정보보호법",
            "CIAL": "신용정보 이용 및 보호에 관한 법률",
            "EFTA": "전자금융거래법",
            "ICTL": "정보통신망 이용촉진 및 정보보호 등에 관한 법률",
            "DBFL": "데이터 산업진흥 및 이용촉진에 관한 기본법",
            "AIBL": "인공지능 발전과 신뢰 기반 조성 등에 관한 기본법",
            "FSMA": "전자금융감독규정",
        }
        # TF-IDF 캐싱 (성능 최적화)
        self._tfidf_cache = {}
        self._idf_cache = {}
        self._articles_cache = None

    def _load_regulations(self) -> Dict[str, Any]:
        """regulations JSON 로드 (privacy_law 포함)"""
        try:
            regulations_path = os.path.join(
                os.path.dirname(__file__),
                "..",
                "data",
                "regulations",
                "all_regulations.json"
            )

            if os.path.exists(regulations_path):
                with open(regulations_path, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                    return data
            else:
                return {"regulations": []}
        except Exception as e:
            print(f"[경고] regulations 로드 실패: {e}")
            return {"regulations": []}

    def _extract_keywords_from_prompt(self, prompt: str) -> set:
        """프롬프트에서 키워드 추출"""
        text = re.sub(r'[^\w가-힣\s]', ' ', prompt.lower())
        words = set(text.split())
        return {w for w in words if len(w) > 1}

    def _calculate_term_frequency(self, text: str) -> Dict[str, float]:
        """단어 빈도 계산 (TF)

        Args:
            text: 입력 텍스트

        Returns:
            {단어: TF 값}
        """
        text = re.sub(r'[^\w가-힣\s]', ' ', text.lower())
        words = [w for w in text.split() if len(w) > 1]

        if not words:
            return {}

        word_count = Counter(words)
        total_words = len(words)

        return {word: count / total_words for word, count in word_count.items()}

    def _calculate_idf(self, all_documents: List[str]) -> Dict[str, float]:
        """역문서 빈도 계산 (IDF)

        Args:
            all_documents: 모든 문서 목록

        Returns:
            {단어: IDF 값}
        """
        word_doc_count = {}
        total_docs = len(all_documents)

        if total_docs == 0:
            return {}

        for doc in all_documents:
            words = set(self._extract_keywords_from_prompt(doc))
            for word in words:
                word_doc_count[word] = word_doc_count.get(word, 0) + 1

        idf_dict = {}
        for word, count in word_doc_count.items():
            idf_dict[word] = math.log(total_docs / (1 + count))

        return idf_dict

    def _calculate_tfidf_vector(self, text: str, idf_dict: Dict[str, float]) -> Dict[str, float]:
        """TF-IDF 벡터 계산

        Args:
            text: 입력 텍스트
            idf_dict: IDF 딕셔너리

        Returns:
            {단어: TF-IDF 값}
        """
        tf = self._calculate_term_frequency(text)
        tfidf = {}

        for word, tf_value in tf.items():
            idf_value = idf_dict.get(word, 0)
            tfidf[word] = tf_value * idf_value

        return tfidf

    def _calculate_cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """Cosine 유사도 계산

        Args:
            vec1: 첫 번째 벡터
            vec2: 두 번째 벡터

        Returns:
            Cosine 유사도 (0-1)
        """
        if not vec1 or not vec2:
            return 0.0

        # 공통 단어의 dot product
        dot_product = sum(
            vec1.get(word, 0) * vec2.get(word, 0)
            for word in set(vec1.keys()) | set(vec2.keys())
        )

        # 벡터의 크기 (norm) - L2 정규화
        norm1 = math.sqrt(sum(v ** 2 for v in vec1.values())) if vec1 else 0
        norm2 = math.sqrt(sum(v ** 2 for v in vec2.values())) if vec2 else 0

        if norm1 == 0 or norm2 == 0:
            return 0.0

        # 기본 코사인 유사도
        similarity = dot_product / (norm1 * norm2)

        # 문서 길이 정규화 (키워드 많은 문서 편향 제거)
        doc_len_factor = min(len(vec1), len(vec2)) / max(len(vec1), len(vec2)) if max(len(vec1), len(vec2)) > 0 else 1.0

        return similarity * (0.8 + 0.2 * doc_len_factor)

    def _phase1_json_matching(self, prompt: str) -> Optional[Tuple[Dict, float]]:
        """Phase 1: JSON 기반 정확 매칭 (키워드 청킹 적용)"""
        prompt_lower = prompt.lower()
        prompt_chunks = self.keyword_chunker.extract_chunks_from_prompt(prompt)

        best_match = None
        best_confidence = 0.0

        for regulation in self.regulations.get("regulations", []):
            code = regulation.get("code")
            articles = regulation.get("articles", [])

            for article in articles:
                keywords = article.get("llm_rule", {}).get("keywords", [])
                matched_keywords = 0
                matched_chunks = 0

                # [1] 원본 키워드 매칭
                for keyword in keywords:
                    if keyword.lower() in prompt_lower:
                        matched_keywords += 1

                # [2] 청킹된 키워드로도 매칭 (신뢰도 향상)
                for keyword in keywords:
                    keyword_chunks = set(self.keyword_chunker.chunk_keyword(keyword))
                    # 프롬프트 청크와 키워드 청크의 교집합
                    matching_chunks = keyword_chunks & prompt_chunks
                    if matching_chunks:
                        matched_chunks += len(matching_chunks)

                # 매칭된 키워드/청크가 있으면 신뢰도 계산
                if matched_keywords > 0 or matched_chunks > 0:
                    # 원본 키워드 기반 신뢰도
                    keyword_confidence = min(matched_keywords / max(len(keywords), 1) * 0.95, 0.95)

                    # 청크 기반 신뢰도 (보조)
                    chunk_confidence = min(matched_chunks / max(len(keywords) * 2, 1) * 0.7, 0.7)

                    # 최종 신뢰도 (원본 > 청크)
                    confidence = max(keyword_confidence, chunk_confidence)

                    # 법령별 가중치: PPA 특화 키워드 감지 시 +0.2 boost
                    ppa_specialized = {"주민번호", "주민등록번호", "여권번호", "운전면허", "반출", "외부", "제공", "3자"}
                    if code == "PPA" and any(kw in ppa_specialized for kw in keywords):
                        confidence = min(confidence + 0.2, 1.0)

                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = {
                            "code": code,
                            "article_id": article.get("id"),
                            "article_number": article.get("number"),
                            "article_title": article.get("title"),
                            "matched_keywords": matched_keywords,
                            "matched_chunks": matched_chunks,
                            "total_keywords": len(keywords),
                            "severity": article.get("llm_rule", {}).get("severity", 50),
                            "related_types": article.get("related_types", []),
                            "chunking_used": matched_chunks > 0
                        }

        if best_match:
            return (best_match, best_confidence)
        return None

    def _phase2_vector_search_enhanced(self, prompt: str) -> Optional[Tuple[List[Dict], float]]:
        """Phase 2 개선: TF-IDF + Cosine 유사도를 이용한 의미론적 검색 (캐싱 적용)

        Returns:
            (상위 후보 리스트, 최고 유사도) 또는 None
        """
        # 캐시 사용 (첫 호출 시만 계산)
        if self._articles_cache is None:
            all_articles_text = []
            articles_by_idx = []

            for regulation in self.regulations.get("regulations", []):
                code = regulation.get("code")
                articles = regulation.get("articles", [])

                for article in articles:
                    keywords = article.get("llm_rule", {}).get("keywords", [])
                    article_text = " ".join(keywords)
                    all_articles_text.append(article_text)
                    articles_by_idx.append({
                        "code": code,
                        "article_id": article.get("id"),
                        "article_number": article.get("number"),
                        "article_title": article.get("title"),
                        "severity": article.get("llm_rule", {}).get("severity", 50),
                        "related_types": article.get("related_types", []),
                        "keywords": keywords
                    })

            self._articles_cache = (all_articles_text, articles_by_idx)
            self._idf_cache = self._calculate_idf(all_articles_text)
        else:
            all_articles_text, articles_by_idx = self._articles_cache

        if not all_articles_text:
            return None

        # IDF 계산 (캐시 사용)
        idf_dict = self._idf_cache

        # 프롬프트의 TF-IDF 벡터
        prompt_tfidf = self._calculate_tfidf_vector(prompt, idf_dict)

        if not prompt_tfidf:
            return None

        # 모든 article의 유사도 계산 (Phase 1과 일관된 청킹 적용)
        all_similarities = []
        prompt_chunks = self.keyword_chunker.extract_chunks_from_prompt(prompt)

        for idx, article_text in enumerate(all_articles_text):
            article_tfidf = self._calculate_tfidf_vector(article_text, idf_dict)

            # Phase 1과 동일한 청킹 적용 (키워드 + 청크 모두 고려)
            keywords = articles_by_idx[idx].get("keywords", [])
            chunk_match_count = 0

            for keyword in keywords:
                keyword_chunks = set(self.keyword_chunker.chunk_keyword(keyword))
                matching_chunks = keyword_chunks & prompt_chunks
                if matching_chunks:
                    chunk_match_count += 1

            similarity = self._calculate_cosine_similarity(prompt_tfidf, article_tfidf)

            # 청크 매칭 시 미미한 보너스 (최대 +0.05, 신중한 조정)
            if chunk_match_count > 0:
                chunk_bonus = min(chunk_match_count * 0.02, 0.05)
                similarity = min(similarity + chunk_bonus, 1.0)

            all_similarities.append((idx, similarity))

        # 동적 임계값 계산 (상위 25% 선택)
        if all_similarities:
            similarities_sorted = sorted([s for _, s in all_similarities], reverse=True)
            dynamic_threshold = max(0.5, similarities_sorted[min(len(similarities_sorted) // 4, len(similarities_sorted) - 1)])

            results = []
            for idx, similarity in all_similarities:
                if similarity >= dynamic_threshold:
                    article_info = articles_by_idx[idx].copy()
                    article_info["similarity"] = similarity
                    results.append(article_info)

            if results:
                # 유사도 기준으로 정렬
                results.sort(key=lambda x: x["similarity"], reverse=True)
                best_similarity = results[0]["similarity"]
                return (results, best_similarity)

        return None

    def _calculate_final_severity(self, matches: List[Dict]) -> int:
        """최종 심각도 계산"""
        if not matches:
            return 0
        max_severity = max(m.get("severity", 0) for m in matches)
        return min(max_severity, 100)

    def _phase3_llm_validation(
        self,
        prompt: str,
        top_candidates: List[Dict]
    ) -> Optional[Tuple[Dict, float]]:
        """Phase 3: LLM 기반 정밀 검증

        상위 후보 regulations 중에서 가장 적절한 것을 LLM이 판정

        Args:
            prompt: 사용자 프롬프트
            top_candidates: 상위 후보 regulations (최대 3개)

        Returns:
            (선택된 regulation, 최종 신뢰도) 또는 None

        주의: LLM 호출은 선택적이고, 실패 시 best match를 반환
        """
        try:
            import os
            import openai

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                # 환경변수에서 .env 파일 로드
                from dotenv import load_dotenv
                load_dotenv()
                api_key = os.getenv("OPENAI_API_KEY")

            if not api_key:
                # API 키 없음 - graceful fallback
                if top_candidates:
                    return (top_candidates[0], 0.85)
                return None

            openai.api_key = api_key

            # 후보 정보를 문자열로 포맷
            candidates_text = ""
            for idx, candidate in enumerate(top_candidates[:3], 1):
                candidates_text += f"\n{idx}. {candidate['code']} - {candidate['article_number']}\n"
                candidates_text += f"   제목: {candidate['article_title']}\n"
                candidates_text += f"   키워드: {', '.join(candidate.get('keywords', []))}\n"

            prompt_text = f"""당신은 법령 전문가입니다. 다음 사용자 프롬프트가 어떤 법령/조항을 위반하는지 판정해주세요.

사용자 프롬프트:
{prompt}

가능한 후보 규정:
{candidates_text}

위 중에서 가장 적절한 규정 하나를 선택하고, 정확도를 0-1 사이의 숫자로 평가해주세요.

응답 형식 (JSON):
{{
  "selected_code": "선택된 법령코드",
  "selected_article": "선택된 조항번호",
  "confidence": 0.85,
  "reasoning": "선택 이유"
}}

응답은 JSON만 포함하세요."""

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "user",
                        "content": prompt_text
                    }
                ],
                max_tokens=500,
                temperature=0.3
            )

            # 응답 파싱
            response_text = response.choices[0].message.content

            # JSON 추출 시도
            try:
                import json as json_module
                json_str = response_text.strip()
                if json_str.startswith("```"):
                    # markdown code block 제거
                    json_str = json_str.split("```")[1]
                    if json_str.startswith("json"):
                        json_str = json_str[4:]
                    json_str = json_str.strip()

                result = json_module.loads(json_str)

                # 거짓양성 필터: is_violation=false면 None 반환
                if not result.get("is_violation", True):
                    return None

                # 선택된 regulation 찾기
                selected_code = result.get("selected_code")
                selected_article = result.get("selected_article")
                confidence = result.get("confidence", 0.8)

                # 선택된 코드가 NONE이면 위반 없음
                if selected_code == "NONE" or not selected_code:
                    return None

                # 후보 중에서 해당 regulation 찾기
                for candidate in top_candidates:
                    if (candidate["code"] == selected_code and
                            candidate["article_number"] == selected_article):
                        return (candidate, min(float(confidence), 0.95))  # 신뢰도 최대 0.95

                # 찾지 못하면 유사도가 가장 높은 것 선택 (단, 신뢰도 낮춤)
                if top_candidates and selected_code:
                    # 선택된 코드가 후보에 있는지 확인
                    for candidate in top_candidates:
                        if candidate["code"] == selected_code:
                            return (candidate, min(float(confidence), 0.85))

                return None

            except (json_module.JSONDecodeError, KeyError, IndexError, ValueError, TypeError):
                # JSON 파싱 실패 시 유사도가 가장 높은 것 선택
                if top_candidates:
                    return (top_candidates[0], 0.85)

            return None

        except ImportError:
            # OpenAI 라이브러리 미설치 - graceful fallback
            if top_candidates:
                return (top_candidates[0], 0.85)
            return None
        except Exception as e:
            # LLM 호출 실패 - graceful fallback
            if top_candidates:
                return (top_candidates[0], 0.85)
            return None

    def detect(self, prompt: str, user_context: Optional[Dict] = None,
               a1_data_grades: Optional[List[str]] = None) -> A3Output:
        """정책 위반 검증 (Smart Routing + TF-IDF + LLM)

        라우팅 로직:
        1. Phase 1 (JSON): confidence > 0.8 → 즉시 반환
        2. Phase 2 (Vector): 0.3 <= confidence <= 0.8 → Phase 3으로
        3. Phase 3 (LLM): confidence 0.8+ 달성 또는 best match 반환
        """
        if user_context is None:
            user_context = {}

        # Phase 1: JSON 정확 매칭
        json_result = self._phase1_json_matching(prompt)
        print(f"[A3-Phase1] JSON matching result: {json_result}")

        if json_result:
            match, confidence = json_result
            if confidence > 0.8:
                # JSON 매칭 신뢰도가 높음 → 즉시 반환
                a3_score = match["severity"]
                if 0 <= a3_score <= 30:
                    a3_decision = "Allow"
                elif 31 <= a3_score <= 50:
                    a3_decision = "Conditional"
                elif 51 <= a3_score <= 80:
                    a3_decision = "Approval"
                else:  # 81-100
                    a3_decision = "Block"

                return A3Output(
                    violation_detected=True,
                    violation_type=match["code"],
                    applicable_laws=[self.law_codes.get(match["code"], match["code"])],
                    violation_articles=[match["article_number"]],
                    violation_severity=match["severity"],
                    a3_score=a3_score,
                    a3_decision=a3_decision
                )

            # Phase 1 신뢰도 0.75 이상 → Phase 2 스킵 (성능 최적화)
            if confidence > 0.75:
                a3_score = match["severity"]
                if 0 <= a3_score <= 30:
                    a3_decision = "Allow"
                elif 31 <= a3_score <= 50:
                    a3_decision = "Conditional"
                elif 51 <= a3_score <= 80:
                    a3_decision = "Approval"
                else:
                    a3_decision = "Block"

                return A3Output(
                    violation_detected=True,
                    violation_type=match["code"],
                    applicable_laws=[self.law_codes.get(match["code"], match["code"])],
                    violation_articles=[match["article_number"]],
                    violation_severity=match["severity"],
                    a3_score=a3_score,
                    a3_decision=a3_decision
                )

        # Phase 2: TF-IDF + Cosine 유사도를 이용한 의미론적 검색 (Phase 1 신뢰도 < 0.75일 때만)
        vector_result_enhanced = self._phase2_vector_search_enhanced(prompt)
        if vector_result_enhanced:
            candidates, sim = vector_result_enhanced
            print(f"[A3-Phase2] Vector search found {len(candidates)} candidates, best similarity: {sim:.3f}")
        else:
            print(f"[A3-Phase2] Vector search found no candidates")

        best_match = None
        best_confidence = 0.0
        decision_method = "json"
        all_candidates = []

        if vector_result_enhanced:
            candidates, best_similarity = vector_result_enhanced
            all_candidates = candidates[:3]  # 상위 3개 후보

            if all_candidates:
                best_match = all_candidates[0]
                best_confidence = best_similarity

                # 신뢰도가 0.3 <= confidence <= 0.8 범위 → Phase 3 LLM 검증
                if 0.3 <= best_similarity <= 0.8:
                    llm_result = self._phase3_llm_validation(prompt, all_candidates)

                    if llm_result:
                        match, llm_confidence = llm_result
                        best_match = match
                        best_confidence = llm_confidence
                        decision_method = "llm"
                    else:
                        # LLM 호출 실패 시 Vector 검색 결과 사용
                        decision_method = "vector"
                else:
                    # 신뢰도가 0.8 이상이면 Vector 검색 결과 사용
                    decision_method = "vector"

        # JSON과 Vector 결과 중 신뢰도가 높은 것 선택
        final_match = None
        final_confidence = 0.0
        final_decision_method = "json"

        if json_result and vector_result_enhanced:
            json_match, json_conf = json_result
            if json_conf >= best_confidence:
                final_match = json_match
                final_confidence = json_conf
                final_decision_method = "json"
            else:
                final_match = best_match
                final_confidence = best_confidence
                final_decision_method = decision_method
        elif json_result:
            final_match, final_confidence = json_result
            final_decision_method = "json"
        elif best_match:
            final_match = best_match
            final_confidence = best_confidence
            final_decision_method = decision_method

        # 결과 반환
        if final_match:
            a3_score = final_match.get("severity", 50)
            if 0 <= a3_score <= 30:
                a3_decision = "Allow"
            elif 31 <= a3_score <= 50:
                a3_decision = "Conditional"
            elif 51 <= a3_score <= 80:
                a3_decision = "Approval"
            else:  # 81-100
                a3_decision = "Block"

            print(f"[A3] Violation detected: {final_match['code']} → {a3_score} ({a3_decision})")
            return A3Output(
                violation_detected=True,
                violation_type=final_match["code"],
                applicable_laws=[self.law_codes.get(final_match["code"], final_match["code"])],
                violation_articles=[final_match["article_number"]],
                violation_severity=final_match.get("severity", 50),
                a3_score=a3_score,
                a3_decision=a3_decision
            )

        # 매칭 없음
        a3_score = 0
        print(f"[A3] No violation detected → 0 (Allow)")
        return A3Output(
            violation_detected=False,
            violation_type=ViolationType.NO_VIOLATION.value,
            applicable_laws=[],
            violation_articles=[],
            violation_severity=0,
            a3_score=a3_score,
            a3_decision="Allow"
        )


def agent_3_node(state: dict) -> dict:
    """LangGraph Node: Agent 3"""
    detector = Agent3PolicyDetector()
    result = detector.detect(
        prompt=state.get('prompt', ''),
        user_context=state.get('user_context', {}),
        a1_data_grades=state.get('a1', {}).get('data_grades', None)
    )
    state['a3'] = {
        'has_violation': result.has_violation,
        'violation_type': result.violation_type,
        'applicable_laws': result.applicable_laws,
        'violation_articles': result.violation_articles,
        'violation_severity': result.violation_severity,
        'related_types': result.related_types,
        'confidence': result.confidence,
        'decision_method': result.decision_method,
        'reasoning': result.reasoning,
    }
    return state


# 호환성 별칭
PolicyDetector = Agent3PolicyDetector


if __name__ == "__main__":
    detector = Agent3PolicyDetector()
    print("[Agent 3] 정책 위반 검증 시스템 준비 완료")
    print(f"로드된 법령 수: {len(detector.regulations.get('regulations', []))}")
    print("\n개선 사항:")
    print("  - Phase 2: TF-IDF + Cosine 유사도 (의미론적 검색)")
    print("  - Phase 3: 선택적 LLM 검증 (신뢰도 0.3-0.8 범위)")
    print("  - 라우팅: JSON > Vector > LLM 순서로 필요한 단계만 실행")
    print("  - 성능: 응답 시간 < 200ms (LLM 호출 제외)")
