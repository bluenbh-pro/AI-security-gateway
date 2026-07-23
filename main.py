"""
Main CLI 진입점

사용법:
    python main.py --input "고객 정보를 외부 AI에 전송해야 합니다" --user-id user_001
    python main.py --interactive  # 대화형 모드
    python main.py --help  # 도움말

구현 상태: [TODO - W3 Day 13-15에서 구현]
"""

import argparse
import json
import sys
from typing import Dict, Any

from core.orchestrator import run_security_gateway

# ============================================================================
# [TODO] 구현 필요 부분:
# 1. argparse로 CLI 인자 처리
# 2. 사용자 입력 및 컨텍스트 수집
# 3. 게이트웨이 실행
# 4. 결과 출력 및 포맷팅
# ============================================================================


def main():
    """메인 CLI 실행"""

    parser = argparse.ArgumentParser(
        description="LLM 보안 게이트웨이 - 프롬프트 모니터링 및 데이터 보호"
    )

    parser.add_argument(
        "--input",
        type=str,
        help="분석할 프롬프트 입력"
    )

    parser.add_argument(
        "--user-id",
        type=str,
        default="anonymous",
        help="사용자 ID (기본값: anonymous)"
    )

    parser.add_argument(
        "--department",
        type=str,
        default="미정",
        help="사용자 부서 (기본값: 미정)"
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="대화형 모드 (반복적 입력)"
    )

    parser.add_argument(
        "--output-format",
        type=str,
        choices=["json", "text"],
        default="text",
        help="출력 포맷 (기본값: text)"
    )

    args = parser.parse_args()

    # [TODO] 구현
    # 1. 단일 입력 모드 처리
    # 2. 대화형 모드 처리
    # 3. 게이트웨이 호출
    # 4. 결과 출력

    if args.input:
        # 단일 입력 모드
        print("[실행] LLM 보안 게이트웨이 분석 중...")
        result = run_security_gateway(
            user_input=args.input,
            user_id=args.user_id,
            user_context={"department": args.department}
        )
        _print_result(result, args.output_format)

    elif args.interactive:
        # 대화형 모드
        print("LLM 보안 게이트웨이 (대화형 모드)")
        print("'quit' 또는 'exit'를 입력하면 종료됩니다.\n")

        while True:
            try:
                user_input = input("> 프롬프트 입력: ").strip()

                if user_input.lower() in ["quit", "exit"]:
                    print("종료합니다.")
                    break

                if not user_input:
                    continue

                result = run_security_gateway(
                    user_input=user_input,
                    user_id=args.user_id,
                    user_context={"department": args.department}
                )
                _print_result(result, args.output_format)
                print()

            except KeyboardInterrupt:
                print("\n종료합니다.")
                break

    else:
        # 기본: 도움말 출력
        parser.print_help()


def _print_result(result: Dict[str, Any], format_type: str = "text"):
    """결과 출력"""

    if format_type == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # 텍스트 포맷
        print("\n" + "=" * 60)
        print(f"의사결정: {result.get('decision', 'N/A')}")
        print(f"위험도: {result.get('risk_score', 'N/A')}/100")
        print(f"출력: {result.get('output', 'N/A')[:100]}...")
        print("=" * 60)


if __name__ == "__main__":
    main()
