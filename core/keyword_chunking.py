#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
키워드 청킹 모듈: 한글 키워드를 의미 있는 단위로 분해

예시:
  "주민등록번호" → ["주민", "등록", "번호", "주민등록번호"]
  "외부 반출" → ["외부", "반출", "외부반출"]
  "3자 제공" → ["3자", "제공", "3자제공"]
"""

import re
from typing import List, Set


class KeywordChunker:
    """한글 키워드 청킹기"""

    def __init__(self):
        """초기화 - 일반적인 한글 단어 패턴 정의"""
        # 2글자 이상의 한글 단어 패턴
        self.hangul_pattern = re.compile(r'[가-힣]+')

        # 자주 사용되는 복합 키워드 사전
        self.compound_keywords = {
            "주민등록번호": ["주민", "등록", "번호"],
            "외부반출": ["외부", "반출"],
            "3자제공": ["3자", "제공"],
            "개인정보": ["개인", "정보"],
            "차별금지": ["차별", "금지"],
            "보안규정": ["보안", "규정"],
            "로그보존": ["로그", "보존"],
            "거래내역": ["거래", "내역"],
            "금융거래": ["금융", "거래"],
        }

    def chunk_keyword(self, keyword: str) -> List[str]:
        """
        단일 키워드를 청크로 분해

        Args:
            keyword: 입력 키워드 (예: "주민등록번호")

        Returns:
            청킹된 리스트 + 원본 (예: ["주민", "등록", "번호", "주민등록번호"])
        """
        chunks = set()
        keyword_lower = keyword.strip().lower()

        # 원본 키워드는 항상 포함
        chunks.add(keyword_lower)

        # 1. 복합 키워드 사전에서 직접 매칭
        if keyword_lower in self.compound_keywords:
            for chunk in self.compound_keywords[keyword_lower]:
                chunks.add(chunk.lower())
            return sorted(list(chunks), key=len, reverse=True)

        # 2. 공백으로 분리
        if " " in keyword_lower:
            for part in keyword_lower.split():
                if len(part) > 0:
                    chunks.add(part)

        # 3. 하이픈으로 분리
        if "-" in keyword_lower:
            for part in keyword_lower.split("-"):
                if len(part) > 0:
                    chunks.add(part)

        # 4. 한글 단어 추출 (형태소 미지원 환경용 간단한 방법)
        hangul_matches = self.hangul_pattern.findall(keyword_lower)
        for match in hangul_matches:
            if len(match) >= 2:  # 2글자 이상만
                chunks.add(match)
                # 2글자씩 윈도우로 추가 (예: "주민등록번호" → "주민", "등록", "번호", "민등", "등록", "록번", "번호")
                for i in range(len(match) - 1):
                    two_char = match[i:i+2]
                    if len(two_char) == 2:
                        chunks.add(two_char)

        # 5. 숫자+단어 조합 처리 (예: "3자제공" → "3자", "제공")
        num_hangul_pattern = re.compile(r'(\d+[가-힣]+|[가-힣]+\d+)')
        for match in num_hangul_pattern.finditer(keyword_lower):
            chunks.add(match.group())
            # 숫자와 한글 분리
            sep = re.split(r'(\d+)', match.group())
            for part in sep:
                if part and len(part) >= 1:
                    chunks.add(part)

        # 길이순으로 정렬 (긴 키워드 먼저)
        return sorted(list(chunks), key=len, reverse=True)

    def chunk_keywords(self, keywords: List[str]) -> Set[str]:
        """
        여러 키워드를 청킹

        Args:
            keywords: 키워드 리스트

        Returns:
            모든 청킹된 키워드 집합
        """
        all_chunks = set()
        for keyword in keywords:
            chunks = self.chunk_keyword(keyword)
            all_chunks.update(chunks)
        return all_chunks

    def extract_chunks_from_prompt(self, prompt: str) -> Set[str]:
        """
        프롬프트에서 유의미한 청크 추출 (토큰을 더 분해)

        Args:
            prompt: 사용자 프롬프트

        Returns:
            프롬프트에서 추출된 청크 집합
        """
        prompt_lower = prompt.lower()
        chunks = set()

        # 공백/기호로 분리한 토큰
        tokens = re.split(r'[\s\-,;.\'"\"()]+', prompt_lower)

        for token in tokens:
            if len(token) >= 1:  # 1글자 이상
                # 원본 토큰 추가
                chunks.add(token)

                # 한글 토큰 추가 분해
                if re.search(r'[가-힣]', token):
                    # 2글자씩 윈도우 (주민번호 → 주민, 민번, 번호)
                    for i in range(len(token) - 1):
                        two_char = token[i:i+2]
                        if len(two_char) == 2:
                            chunks.add(two_char)
                    # 3글자씩도 추가
                    for i in range(len(token) - 2):
                        three_char = token[i:i+3]
                        if len(three_char) == 3:
                            chunks.add(three_char)

                # 숫자+한글 분리 (3자제공 → 3, 자, 제공, ...)
                if re.search(r'\d[가-힣]|[가-힣]\d', token):
                    parts = re.split(r'(\d+)', token)
                    for part in parts:
                        if part and len(part) >= 1:
                            chunks.add(part)

        # 빈 문자열 제거
        return {c for c in chunks if c}


def create_keyword_chunks(keywords: List[str]) -> List[List[str]]:
    """
    각 키워드별 청크 리스트 생성 (JSON 저장용)

    Args:
        keywords: 원본 키워드 리스트

    Returns:
        [["키워드1_청크1", "키워드1_청크2"], ["키워드2_청크1", ...]] 형태
    """
    chunker = KeywordChunker()
    return [chunker.chunk_keyword(kw) for kw in keywords]


# 테스트
if __name__ == "__main__":
    chunker = KeywordChunker()

    print("=" * 80)
    print("키워드 청킹 테스트")
    print("=" * 80)

    test_keywords = [
        "주민등록번호",
        "외부반출",
        "3자제공",
        "거래내역",
        "금융거래정보",
        "차별금지",
    ]

    for keyword in test_keywords:
        chunks = chunker.chunk_keyword(keyword)
        print(f"\n[{keyword}]")
        print(f"  청크: {chunks}")

    print("\n" + "=" * 80)
    print("프롬프트 청킹 테스트")
    print("=" * 80)

    test_prompt = "고객의 주민등록번호가 포함된 파일을 외부로 반출하고 싶어. 가능해?"
    chunks = chunker.extract_chunks_from_prompt(test_prompt)
    print(f"\n프롬프트: {test_prompt}")
    print(f"추출된 청크: {sorted(chunks)}")
