#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Golden Dataset 기대값 표준화
마스킹 → 조건부허용으로 통합 (v2 4단계 구조에 맞춤)
"""

import json

def standardize_decisions(input_path: str, output_path: str) -> None:
    """기대값의 마스킹을 조건부허용으로 변경"""

    print(f"Loading: {input_path}")

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    test_cases = data.get("test_cases", [])
    print(f"Total cases: {len(test_cases)}")

    # 기대값 의사결정 통계
    before_dist = {}
    for case in test_cases:
        d = case.get('expected_decision')
        before_dist[d] = before_dist.get(d, 0) + 1

    print("\nBefore standardization:")
    for d in ['허용', '조건부허용', '마스킹', '승인요청', '차단']:
        count = before_dist.get(d, 0)
        print(f"  {d}: {count}")

    # 마스킹 → 조건부허용으로 변경
    changed = 0
    for case in test_cases:
        if case.get('expected_decision') == '마스킹':
            case['expected_decision'] = '조건부허용'
            changed += 1

    # 변경 후 통계
    after_dist = {}
    for case in test_cases:
        d = case.get('expected_decision')
        after_dist[d] = after_dist.get(d, 0) + 1

    print("\nAfter standardization:")
    for d in ['허용', '조건부허용', '승인요청', '차단']:
        count = after_dist.get(d, 0)
        print(f"  {d}: {count}")

    print(f"\nChanged: {changed} cases (마스킹 → 조건부허용)")

    # 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Saved: {output_path}")

if __name__ == "__main__":
    standardize_decisions("data/golden_dataset.json", "data/golden_dataset.json")
    print("\nOK: Decisions standardized to 4-stage structure!")
