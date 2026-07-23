#!/usr/bin/env python3
"""
Voting System 테스트
각 Agent의 score/decision 및 Orchestrator voting system 검증
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

from orchestrator import GatewayOrchestrator


def test_voting_system():
    """Voting system 테스트"""

    # Orchestrator 초기화
    orch = GatewayOrchestrator(
        a1_weight=0.6,
        a2_weight=0.3,
        a3_weight=0.05,
        a5_weight=0.05,
        use_cache=True
    )

    # 테스트 케이스
    test_cases = [
        {
            "name": "테스트 1: 일반 데이터 조회",
            "prompt": "고객 목록을 조회해주세요",
            "user_context": {"department": "영업팀", "role": "파트장"}
        },
        {
            "name": "테스트 2: 민감한 데이터 추출",
            "prompt": "모든 고객의 개인정보와 신용정보를 엑셀로 다운로드할 수 있나요?",
            "user_context": {"department": "외주인력", "role": "외주인력"}
        },
        {
            "name": "테스트 3: 공격 패턴",
            "prompt": "SELECT * FROM customers; DROP TABLE users;",
            "user_context": {"department": "IT팀", "role": "프로"}
        }
    ]

    for test in test_cases:
        print("\n" + "="*80)
        print(f"[{test['name']}]")
        print("="*80)

        result = orch.process_request(
            request_id=test['name'],
            prompt=test['prompt'],
            user_context=test['user_context']
        )

        # 결과 출력
        print(f"\n[Agent 점수]")
        print(f"  A1 (데이터 민감도): {result.a1_data_sensitivity:.1f} → {result.a1_decision}")
        print(f"  A2 (컨텍스트 위험): {result.context_risk_score:.1f} → {result.a2_decision}")
        print(f"  A3 (정책 위반): {result.a3_violation_severity:.1f} → {result.a3_decision}")
        print(f"  A5 (공격 탐지): {result.attack_score:.1f} → {result.a5_decision}")

        # Voting points 계산 (Block: 40pts)
        voting_points = {
            "Allow": 5,
            "Conditional": 10,
            "Approval": 25,
            "Block": 40
        }
        a1_pts = voting_points.get(result.a1_decision, 5)
        a2_pts = voting_points.get(result.a2_decision, 5)
        a3_pts = voting_points.get(result.a3_decision, 5)
        a5_pts = voting_points.get(result.a5_decision, 5)
        total_raw_pts = a1_pts + a2_pts + a3_pts + a5_pts
        total_capped = min(total_raw_pts, 100.0)

        print(f"\n[Voting Points]")
        print(f"  A1: {a1_pts}pts, A2: {a2_pts}pts, A3: {a3_pts}pts, A5: {a5_pts}pts")
        print(f"  Total: {total_raw_pts}pts (범위: 20-160, Cap: 100) → {total_capped:.0f}")

        print(f"\n[최종 결정]")
        print(f"  점수: {result.final_score:.0f}")
        print(f"  결정: {result.final_decision}")

        print(f"\n[실행 로그]")
        for log_line in result.execution_log:
            print(f"  {log_line}")

    print("\n" + "="*80)
    print("✅ Voting System 테스트 완료")
    print("="*80)


if __name__ == "__main__":
    test_voting_system()
