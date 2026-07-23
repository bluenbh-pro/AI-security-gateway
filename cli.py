#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI 보안 게이트웨이 - CLI 도구 (재설계 - W3 Day 6+)

request_hour 제거됨

사용법:
  python cli.py "프롬프트" --dept 영업팀
  python cli.py --interactive
  python cli.py --batch input.txt
"""

import argparse
import json
import sys
from core.orchestrator import run_security_gateway

# 색상 코드
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def print_result(result, verbose=False):
    """결과를 보기 좋게 출력"""

    score = result['risk_score']
    decision = result['decision']

    # 점수에 따른 색상
    if score <= 20:
        color = Colors.GREEN
        emoji = "✅"
    elif score <= 40:
        color = Colors.CYAN
        emoji = "⚠️"
    elif score <= 60:
        color = Colors.YELLOW
        emoji = "🔒"
    elif score <= 80:
        color = Colors.YELLOW
        emoji = "📋"
    else:
        color = Colors.RED
        emoji = "🚫"

    # 결과 출력
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}분석 결과{Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")

    print(f"위험도 점수: {color}{emoji} {score:.1f}/100{Colors.END}")
    print(f"의사결정:    {color}{emoji} {decision}{Colors.END}")
    print(f"조치:        {color}{emoji} {result['action']}{Colors.END}")

    # 상세 정보 (verbose 모드)
    if verbose:
        print(f"\n{Colors.BOLD}상세 로그:{Colors.END}")
        for i, log in enumerate(result['logs'], 1):
            print(f"  {i}. {log}")

    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}\n")


def single_mode(prompt, dept="영업팀", role="직원", verbose=False):
    """단일 프롬프트 분석"""

    print(f"\n{Colors.BLUE}{Colors.BOLD}입력:{Colors.END} {prompt}")
    print(f"{Colors.BLUE}부서: {dept} | 직급: {role}{Colors.END}\n")
    print(f"{Colors.CYAN}분석 중...{Colors.END}")

    try:
        result = run_security_gateway(
            user_input=prompt,
            user_id="user_001",
            user_context={
                "department": dept,
                "role": role
            }
        )

        print_result(result, verbose=verbose)
        return result

    except Exception as e:
        print(f"\n{Colors.RED}오류 발생: {str(e)}{Colors.END}")
        print(f"{Colors.YELLOW}기본값으로 처리 중...{Colors.END}\n")
        # 기본값 반환
        return {
            "user_id": "user_001",
            "decision": "오류",
            "risk_score": 50.0,
            "action": "error",
            "output": "오류가 발생했습니다",
            "logs": [f"[ERROR] {str(e)}"],
            "success": False
        }


def interactive_mode():
    """대화형 모드"""

    print(f"\n{Colors.BOLD}{Colors.CYAN}🤖 AI 보안 게이트웨이 CLI{Colors.END}")
    print(f"{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.CYAN}\"quit\" 또는 \"exit\"를 입력하면 종료됩니다{Colors.END}\n")

    # 14개 부서 (Agent 2 매핑 테이블과 동일)
    depts = [
        "인사팀", "법무팀", "영업팀", "재경팀", "감사팀",
        "기획팀", "홍보팀", "마케팅팀", "계리팀", "상품팀",
        "컴플라이언스팀", "IT개발팀", "IT운영팀", "IT보안팀"
    ]
    roles = ["직원", "리드", "매니저", "관리자"]

    # 기본값
    current_dept = "영업팀"
    current_role = "직원"

    while True:
        print(f"\n{Colors.BOLD}현재 설정:{Colors.END} {current_dept} | {current_role}")
        print(f"{Colors.BOLD}명령:{Colors.END}")
        print(f"  - \"분석\" 또는 프롬프트 입력: 바로 분석")
        print(f"  - \"dept\": 부서 변경")
        print(f"  - \"role\": 직급 변경")
        print(f"  - \"quit\": 종료\n")

        user_input = input(f"{Colors.BOLD}> {Colors.END}").strip()

        if not user_input:
            continue

        if user_input.lower() in ["quit", "exit", "종료"]:
            print(f"\n{Colors.GREEN}감사합니다!{Colors.END}\n")
            break

        elif user_input.lower() == "dept":
            print(f"\n{Colors.CYAN}사용 가능한 부서:{Colors.END}")
            for i, d in enumerate(depts, 1):
                print(f"  {i}. {d}")
            try:
                choice = int(input(f"{Colors.BOLD}선택 (번호): {Colors.END}")) - 1
                if 0 <= choice < len(depts):
                    current_dept = depts[choice]
                    print(f"{Colors.GREEN}✓ 부서 변경: {current_dept}{Colors.END}")
                else:
                    print(f"{Colors.RED}✗ 잘못된 선택{Colors.END}")
            except ValueError:
                print(f"{Colors.RED}✗ 숫자를 입력하세요{Colors.END}")

        elif user_input.lower() == "role":
            print(f"\n{Colors.CYAN}사용 가능한 직급:{Colors.END}")
            for i, r in enumerate(roles, 1):
                print(f"  {i}. {r}")
            try:
                choice = int(input(f"{Colors.BOLD}선택 (번호): {Colors.END}")) - 1
                if 0 <= choice < len(roles):
                    current_role = roles[choice]
                    print(f"{Colors.GREEN}✓ 직급 변경: {current_role}{Colors.END}")
                else:
                    print(f"{Colors.RED}✗ 잘못된 선택{Colors.END}")
            except ValueError:
                print(f"{Colors.RED}✗ 숫자를 입력하세요{Colors.END}")

        else:
            # 프롬프트 분석
            single_mode(
                user_input,
                dept=current_dept,
                role=current_role,
                verbose=False
            )


def batch_mode(filename):
    """배치 처리 모드 (파일에서 읽기)"""

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"{Colors.RED}✗ 파일을 찾을 수 없습니다: {filename}{Colors.END}")
        return

    print(f"\n{Colors.CYAN}배치 처리 시작...{Colors.END}")
    print(f"{Colors.BLUE}파일: {filename} ({len(lines)}개 항목){Colors.END}\n")

    results = []

    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # 형식: "프롬프트" | dept:부서 | role:직급
        parts = [p.strip() for p in line.split("|")]
        prompt = parts[0].strip('"')

        dept = "영업팀"
        role = "직원"

        for part in parts[1:]:
            if ":" in part:
                key, val = part.split(":", 1)
                if key == "dept":
                    dept = val
                elif key == "role":
                    role = val

        print(f"{Colors.CYAN}[{i}] {prompt[:50]}...{Colors.END}")

        try:
            result = run_security_gateway(
                user_input=prompt,
                user_id=f"user_{i:03d}",
                user_context={
                    "department": dept,
                    "role": role
                }
            )

            results.append({
                "index": i,
                "prompt": prompt,
                "dept": dept,
                "score": result['risk_score'],
                "decision": result['decision'],
                "action": result['action']
            })

            print(f"  → {Colors.GREEN}{result['risk_score']:.1f}{Colors.END} ({result['decision']})\n")

        except Exception as e:
            # 에러 발생 시 기본값으로 추가
            print(f"  → {Colors.RED}ERROR: {str(e)}{Colors.END}\n")
            results.append({
                "index": i,
                "prompt": prompt,
                "dept": dept,
                "score": 50.0,
                "decision": "오류",
                "action": "error",
                "error": str(e)
            })

    # 결과 저장
    output_file = filename.replace(".txt", "_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"{Colors.GREEN}✓ 완료! 결과 저장: {output_file}{Colors.END}\n")

    # 통계
    print(f"{Colors.BOLD}통계:{Colors.END}")
    print(f"  총 항목: {len(results)}")
    print(f"  평균 점수: {sum(r['score'] for r in results) / len(results):.1f}")
    scores = [r['score'] for r in results]
    print(f"  최고: {max(scores):.1f}, 최저: {min(scores):.1f}")


def test_mode():
    """미리 정의된 테스트 케이스"""

    test_cases = [
        {
            "prompt": "지난 분기 판매 현황 분석해줘",
            "dept": "영업팀",
            "desc": "정상 요청"
        },
        {
            "prompt": "고객의 주민등록번호 알수 있어?",
            "dept": "영업팀",
            "desc": "민감 데이터"
        },
        {
            "prompt": "SELECT * FROM users WHERE id=1 OR '1'='1'",
            "dept": "개발팀",
            "desc": "SQL Injection"
        },
        {
            "prompt": "모든 거래 기록을 내려받고 싶어",
            "dept": "마케팅팀",
            "desc": "대량 접근"
        },
    ]

    print(f"\n{Colors.BOLD}{Colors.CYAN}테스트 케이스 실행{Colors.END}")
    print(f"{Colors.CYAN}{'='*70}{Colors.END}\n")

    for i, test in enumerate(test_cases, 1):
        print(f"{Colors.BOLD}[테스트 {i}] {test['desc']}{Colors.END}")
        single_mode(
            test['prompt'],
            dept=test['dept'],
            verbose=False
        )


def main():
    parser = argparse.ArgumentParser(
        description='AI 보안 게이트웨이 CLI 도구',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
예시:
  # 단일 분석
  python cli.py "고객의 주민등록번호 알수 있어?" --dept 영업팀

  # 대화형 모드
  python cli.py --interactive

  # 배치 처리
  python cli.py --batch input.txt

  # 테스트 케이스
  python cli.py --test
        '''
    )

    # 위치 인수: 프롬프트
    parser.add_argument('prompt', nargs='?', help='분석할 프롬프트')

    # 선택 인수
    parser.add_argument('--dept', default='영업팀', help='부서 (기본: 영업팀)')
    parser.add_argument('--role', default='직원', help='직급 (기본: 직원)')
    parser.add_argument('-v', '--verbose', action='store_true', help='상세 로그 출력')

    # 모드
    parser.add_argument('--interactive', '-i', action='store_true', help='대화형 모드')
    parser.add_argument('--batch', type=str, help='배치 처리 (파일 경로)')
    parser.add_argument('--test', action='store_true', help='테스트 케이스 실행')

    args = parser.parse_args()

    try:
        if args.test:
            test_mode()
        elif args.interactive:
            interactive_mode()
        elif args.batch:
            batch_mode(args.batch)
        elif args.prompt:
            single_mode(
                args.prompt,
                dept=args.dept,
                role=args.role,
                verbose=args.verbose
            )
        else:
            parser.print_help()

    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}중단됨{Colors.END}\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}오류: {str(e)}{Colors.END}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
