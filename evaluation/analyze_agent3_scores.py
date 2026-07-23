#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Agent 3 점수 분포 분석

벤치마크 결과에서 Agent 3의 점수가 어떻게 분포하는지 확인합니다.
"""

import json
from collections import Counter


def analyze_agent3():
    """Agent 3 점수 분포 분석"""
    # 벤치마크 결과 로드
    with open("evaluation/benchmark_results.json", 'r', encoding='utf-8') as f:
        benchmark = json.load(f)

    detailed_results = benchmark.get("detailed_results", [])

    print("=" * 80)
    print("[ANALYSIS] Agent 3 (Policy Risk) Score Distribution")
    print("=" * 80)

    # Agent 3 점수 수집
    agent3_scores = []
    zero_count = 0
    nonzero_count = 0

    for result in detailed_results:
        score = result.get("agent3_score", 0)
        agent3_scores.append(score)

        if score == 0:
            zero_count += 1
        else:
            nonzero_count += 1

    # 기본 통계
    print(f"\n[STATS] Basic Statistics:")
    print(f"  Total cases: {len(agent3_scores)}")
    print(f"  Zero scores (0.0): {zero_count} ({zero_count/len(agent3_scores)*100:.1f}%)")
    print(f"  Non-zero scores: {nonzero_count} ({nonzero_count/len(agent3_scores)*100:.1f}%)")

    # 점수 분포
    if agent3_scores:
        print(f"\n[DISTRIBUTION] Agent 3 Score Range:")
        print(f"  Min: {min(agent3_scores):.2f}")
        print(f"  Max: {max(agent3_scores):.2f}")
        print(f"  Mean: {sum(agent3_scores)/len(agent3_scores):.2f}")
        print(f"  Median: {sorted(agent3_scores)[len(agent3_scores)//2]:.2f}")

    # 점수별 횟수 (구간별)
    print(f"\n[HISTOGRAM] Score Distribution by Range:")
    ranges = [
        (0, 0, "0 (정책 위반 없음)"),
        (0.01, 20, "0.01-20 (매우 낮음)"),
        (20.01, 40, "20.01-40 (낮음)"),
        (40.01, 60, "40.01-60 (중간)"),
        (60.01, 80, "60.01-80 (높음)"),
        (80.01, 100, "80.01-100 (매우 높음)")
    ]

    for min_val, max_val, label in ranges:
        count = 0
        for score in agent3_scores:
            if min_val == 0 and max_val == 0:
                if score == 0:
                    count += 1
            else:
                if min_val < score <= max_val:
                    count += 1

        if count > 0:
            pct = count / len(agent3_scores) * 100
            print(f"  {label}: {count:3d} ({pct:5.1f}%)")

    # 정책 위반 감지 현황
    print(f"\n[DETECTION] Policy Violation Detection Rate:")

    # Golden Dataset에서 정책 위반이 있는 케이스 확인
    with open("data/golden_dataset_v3_rubric.json", 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    test_cases = dataset.get("test_cases", [])

    # 케이스별로 agent3_score와 실제 정책 위반 여부 비교
    policy_violations_in_dataset = 0
    correctly_detected = 0

    for test_case in test_cases:
        case_id = test_case.get("case_id")
        rubric_score = test_case.get("rubric_score", 1)

        # Rubric에서 정책 위반이 반영된 케이스 (Rubric score 4, 5)
        has_policy_risk = rubric_score >= 4

        # 해당 케이스의 agent3_score 찾기
        for result in detailed_results:
            if result.get("case_id") == case_id:
                agent3_score = result.get("agent3_score", 0)

                if has_policy_risk:
                    policy_violations_in_dataset += 1
                    if agent3_score > 0:
                        correctly_detected += 1

                break

    if policy_violations_in_dataset > 0:
        detection_rate = correctly_detected / policy_violations_in_dataset * 100
        print(f"  Expected policy violations: {policy_violations_in_dataset}")
        print(f"  Correctly detected (agent3_score > 0): {correctly_detected}")
        print(f"  Detection rate: {detection_rate:.1f}%")
    else:
        print(f"  No policy violations in Rubric-based dataset")

    # 상세 분석
    print(f"\n[DIAGNOSIS] Diagnosis:")
    if zero_count / len(agent3_scores) > 0.95:
        print(f"  [PROBLEM] Agent 3 is NOT working properly!")
        print(f"  → {zero_count}개 케이스 중 {zero_count}개가 0점")
        print(f"  → Agent 3의 정책 감지 로직이 작동하지 않음")
        print(f"  → 가중치 조정만으로는 개선 불가능")
        print(f"\n  [SOLUTION] Agent 3 점수 계산 로직을 개선해야 함")
        return False
    else:
        print(f"  [OK] Agent 3 is working")
        print(f"  → Zero scores: {zero_count/len(agent3_scores)*100:.1f}%")
        print(f"  → Non-zero scores: {nonzero_count/len(agent3_scores)*100:.1f}%")
        print(f"  → 가중치 조정으로 영향력 증대 가능")
        return True


if __name__ == "__main__":
    is_agent3_working = analyze_agent3()

    print("\n" + "=" * 80)
    print("[CONCLUSION]")
    if is_agent3_working:
        print("✓ Agent 3 is working → Proceed to weight optimization")
    else:
        print("✗ Agent 3 needs improvement → Fix Agent 3 first")
    print("=" * 80)
