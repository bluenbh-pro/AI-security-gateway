#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
최종 Dataset 생성: Benchmark 결과 기반

Benchmark에서 얻은 Agent별 실제 점수를 사용해서
Rubric V2 공식으로 expected 값을 재계산합니다.

이렇게 하면:
1. Golden Dataset과 Benchmark의 불일치 해결
2. Rubric V2 공식 정확성 보장 (0.4, 0.3, 0.3 가중치)
"""

import json


def finalize_dataset():
    """Dataset 최종화"""
    # Benchmark 결과 로드
    with open("evaluation/benchmark_results.json", 'r', encoding='utf-8') as f:
        benchmark = json.load(f)

    # Golden Dataset 로드
    with open("data/golden_dataset.json", 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    detailed_results = benchmark.get("detailed_results", [])
    test_cases = dataset.get("test_cases", [])

    print(f"[FINAL] Finalizing dataset from benchmark results...")
    print(f"[FINAL] Processing {len(test_cases)} test cases")

    # 케이스별로 벤치마크 결과 매핑
    results_by_id = {r["case_id"]: r for r in detailed_results}

    # Rubric V2 공식 적용
    # final_score = agent1 × 0.4 + agent3 × 0.3 + agent2 × 0.3
    updated_count = 0

    for test_case in test_cases:
        case_id = test_case.get("case_id")
        bench_result = results_by_id.get(case_id)

        if not bench_result:
            continue

        try:
            # Agent별 실제 점수
            agent1_score = bench_result.get("agent1_score", 0)
            agent3_score = bench_result.get("agent3_score", 0)
            agent2_score = bench_result.get("agent2_score", 0)

            # Rubric V2 공식 적용
            expected_risk = (
                agent1_score * 0.40 +
                agent3_score * 0.30 +
                agent2_score * 0.30
            )

            # 의사결정 매핑
            if expected_risk <= 30:
                expected_decision = "Allow"
            elif expected_risk <= 55:
                expected_decision = "Conditional Allow"
            elif expected_risk <= 85:
                expected_decision = "Approval Required"
            else:
                expected_decision = "Block"

            # 업데이트
            test_case["expected_risk"] = round(expected_risk, 2)
            test_case["expected_decision"] = expected_decision
            test_case["components"] = {
                "agent1_score": round(agent1_score, 2),
                "agent3_score": round(agent3_score, 2),
                "agent2_score": round(agent2_score, 2)
            }

            updated_count += 1

        except Exception as e:
            print(f"[ERROR] Case {case_id}: {str(e)}")

    # 저장
    output_path = "data/golden_dataset_final.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Updated {updated_count}/{len(test_cases)} cases")
    print(f"[OK] Saved to: {output_path}")

    # 통계
    from collections import Counter
    decisions = Counter(tc.get("expected_decision") for tc in test_cases)
    scores = [tc.get("expected_risk", 0) for tc in test_cases]

    print(f"\n[STATS] Decision Distribution:")
    for decision in ["Allow", "Conditional Allow", "Approval Required", "Block"]:
        count = decisions.get(decision, 0)
        pct = count / len(test_cases) * 100
        print(f"  {decision}: {count:3d} ({pct:5.1f}%)")

    print(f"\n[STATS] Risk Score Distribution:")
    print(f"  Min: {min(scores):.0f}")
    print(f"  Max: {max(scores):.0f}")
    print(f"  Mean: {sum(scores)/len(scores):.0f}")


if __name__ == "__main__":
    finalize_dataset()
    print(f"\n[SUCCESS] Final dataset complete!")
