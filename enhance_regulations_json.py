#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
from pathlib import Path
from datetime import datetime

# ===== Type별 상세 정보 (policy_mapping.md에서 추출) =====
TYPE_DETAILS = {
    "Type_1": {
        "keywords": ["극비", "대외비", "confidential", "secret", "전략", "계획", "정책", "지침"],
        "violation_logic": "파일_첨부 AND (극비|대외비) AND (번역|요약|편집|영어로)",
        "related_laws": ["영업비밀법", "PPFL"],
        "severity": 85,
        "action": "차단"
    },
    "Type_2": {
        "keywords": ["신용점수", "신용도", "대출", "여신", "채무", "credit score", "주민번호", "이메일", "고객ID"],
        "violation_logic": "신용정보_포함 OR (개인정보_여러개_결합)",
        "related_laws": ["신용정보법", "PPFL", "DBFL"],
        "severity": 95,
        "action": "차단"
    },
    "Type_3": {
        "keywords": ["정책", "규정", "지침", "매뉴얼", "접근통제", "보안", "모니터링"],
        "violation_logic": "(회사정책_설명) AND (구체적_기준_공개) AND (보안_메커니즘_포함)",
        "related_laws": ["영업비밀법"],
        "severity": 70,
        "action": "승인필요"
    },
    "Type_4": {
        "keywords": ["거래", "거래기록", "송금", "입금", "출금", "계좌", "카드번호", "고객", "개인정보"],
        "violation_logic": "거래데이터_첨부 AND (개인정보 OR 신용정보)",
        "related_laws": ["PPFL", "신용정보법", "EFTA", "DBFL"],
        "severity": 92,
        "action": "차단"
    },
    "Type_5": {
        "keywords": ["프로세스", "절차", "알고리즘", "모델", "기준", "가중치"],
        "violation_logic": "(회사절차_설명 OR 알고리즘_로직) AND 외부_LLM",
        "related_laws": ["영업비밀법"],
        "severity": 72,
        "action": "승인필요"
    },
    "Type_6": {
        "keywords": ["정책", "방침", "규정", "개인정보", "보호", "compli...", "저장", "암호화"],
        "violation_logic": "(고객규모_공개 OR 저장위치_공개 OR 권한자규모_공개)",
        "related_laws": ["PPFL"],
        "severity": 60,
        "action": "승인필요"
    },
    "Type_7": {
        "keywords": [".py", ".js", ".java", "auth", "token", "key", "secret", "password"],
        "violation_logic": "코드파일_첨부 AND (내부코드 OR auth|token|secret)",
        "related_laws": ["영업비밀법", "ICTL"],
        "severity": 88,
        "action": "차단"
    },
    "Type_8": {
        "keywords": ["생성", "만들어", "가짜", "샘플", "테스트", "더미", "이름", "주민번호"],
        "violation_logic": "개인정보_구조_공개 AND 샘플데이터_생성_요청",
        "related_laws": ["PPFL"],
        "severity": 65,
        "action": "조건부허용"
    },
    "Type_9": {
        "keywords": ["극비", "대외비", "confidential", "번역", "변환", "편집", "요약"],
        "violation_logic": "파일_첨부 AND (극비 OR 대외비) AND (번역 OR 변환)",
        "related_laws": ["영업비밀법"],
        "severity": 82,
        "action": "차단"
    },
    "Type_10": {
        "keywords": [".csv", ".xlsx", "정제", "중복제거", "이상치", "고객", "이름"],
        "violation_logic": "데이터파일_첨부 AND 개인정보_포함",
        "related_laws": ["PPFL", "DBFL"],
        "severity": 78,
        "action": "차단"
    },
    "Type_11": {
        "keywords": ["계좌", "계좌번호", "입금", "출금", "송금", "자금"],
        "violation_logic": "계좌정보_포함 OR 자금거래_정보_포함",
        "related_laws": ["EFTA", "ICTL"],
        "severity": 90,
        "action": "차단"
    },
    "Type_12": {
        "keywords": ["CEO", "회장", "임원", "경영진", "주민번호", "신용점수", "거래"],
        "violation_logic": "(임원명_공개 OR 구체적인_개인명) AND (신용정보 OR 거래정보)",
        "related_laws": ["PPFL", "신용정보법"],
        "severity": 93,
        "action": "차단"
    },
    "Type_13": {
        "keywords": ["우회", "회피", "방법", "가능", "문제없이", "법적으로", "제공"],
        "violation_logic": "(규정회피_명시 OR 법령우회_방안요청) AND (민감정보_제공_의도)",
        "related_laws": ["신용정보법", "PPFL"],
        "severity": 99,
        "action": "차단"
    },
    "Type_14": {
        "keywords": ["침입", "우회", "해킹", "보안", "취약점", "공격", "IP", "포트"],
        "violation_logic": "(보안_우회_방법_질문 OR 침입_시도) AND (시스템_아키텍처_공개)",
        "related_laws": ["ICTL"],
        "severity": 98,
        "action": "차단"
    },
    "Type_15": {
        "keywords": ["머신러닝", "알고리즘", "방식", "기술", "베스트프래틱스"],
        "violation_logic": "(민감정보_없음) AND (회사특화정보_없음)",
        "related_laws": [],
        "severity": 0,
        "action": "허용"
    }
}

LAW_CODE_MAP = {
    "영업비밀법": "BSL",
    "PPFL": "PPFL",
    "신용정보법": "CIAL",
    "EFTA": "EFTA",
    "ICTL": "ICTL",
    "DBFL": "DBFL",
}

def enhance_regulations_json():
    """regulations_new.json을 개선하여 더 풍부한 정보 추가"""

    input_path = Path(r"C:\AI_Gateway\regulations_new.json")

    if not input_path.exists():
        print(f"Error: {input_path} not found")
        return

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Type별 Type 관계도 추가
    print("Enhancing regulations JSON...")

    # 각 조항에 대해 Type별 관련도 정보 보강
    for regulation in data["regulations"]:
        for article in regulation["articles"]:
            article_num = article["number"]
            law_code = article["id"].split("_")[0]

            # 기존 related_types 정보 유지하며 보강
            enhanced_types = {}
            for type_key, type_info in TYPE_DETAILS.items():
                if law_code in [LAW_CODE_MAP.get(law, law) for law in type_info["related_laws"]]:
                    if article_num in TYPE_DETAILS[type_key].get("related_articles", []) or \
                       article_num in ["제3조", "제8조", "제15조", "제17조", "제18조", "제21조", "제25조", "제28조", "제34조", "제35조", "제48조"]:
                        enhanced_types[type_key] = TYPE_DETAILS[type_key]["severity"]

            # llm_rule 보강
            article["llm_rule"]["keywords"] = list(set(
                article["llm_rule"]["keywords"] +
                [kw for type_key in article.get("related_types", [])
                 if type_key in TYPE_DETAILS
                 for kw in TYPE_DETAILS[type_key]["keywords"][:3]]
            ))

            # violation_logic 개선
            if article.get("related_types"):
                primary_type = article["related_types"][0]
                if primary_type in TYPE_DETAILS:
                    article["llm_rule"]["violation_logic"] = TYPE_DETAILS[primary_type]["violation_logic"]

    # 메타데이터 보강
    data["metadata"]["structure_version"] = "2.1"
    data["metadata"]["enhancement_date"] = datetime.now().strftime("%Y-%m-%d")
    data["metadata"]["type_coverage"] = list(TYPE_DETAILS.keys())

    output_path = Path(r"C:\AI_Gateway\regulations_new.json")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[OK] Enhanced JSON saved to: {output_path}")
    print(f"  - Total Types covered: {len(TYPE_DETAILS)}")
    print(f"  - Last updated: {datetime.now().strftime('%Y-%m-%d')}")

if __name__ == "__main__":
    enhance_regulations_json()
