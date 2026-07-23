#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
from collections import defaultdict

# Define action keywords
READ_KEYWORDS = [
    '조회', '확인', '살펴', '검색', '보기', '읽기', '분석', '보고',
    '리포트', '통계', '현황', '파악', '봐', '봐줄', '살펴봐',
    'check', 'view', 'search', 'look', 'read', 'analyze', 'report',
    'statistics', 'status', 'retrieve', 'fetch', 'get', 'query'
]

WRITE_KEYWORDS = [
    '변경', '수정', '저장', '업데이트', '생성', '삭제', '추가', '제거',
    '이동', '복사', '입력', '쓰기', '변경', '할당',
    'update', 'create', 'delete', 'save', 'remove', 'add', 'change',
    'modify', 'write', 'insert', 'drop', 'alter', 'assign'
]

def analyze_prompt(prompt):
    """
    분석: 프롬프트에서 READ와 WRITE 액션을 검출

    반환값: ('read_only', 'contains_write', 'mixed')
    """
    prompt_lower = prompt.lower()

    has_read = any(keyword in prompt_lower for keyword in READ_KEYWORDS)
    has_write = any(keyword in prompt_lower for keyword in WRITE_KEYWORDS)

    if has_write:
        return 'contains_write'
    elif has_read:
        return 'read_only'
    else:
        # 키워드가 없으면 기본적으로 safe한 것으로 간주
        return 'safe_by_default'

def determine_decision(prompt, original_decision):
    """
    프롬프트 분석을 기반으로 expected_decision 결정
    """
    action_type = analyze_prompt(prompt)

    if action_type == 'contains_write':
        # WRITE 액션이 있으면 block 유지
        return 'block'
    elif action_type == 'read_only':
        # READ 액션만 있으면 approval
        return 'approval'
    else:
        # 키워드가 없으면 원래 결정 유지 (민감도 기반 판정은 Agent가 함)
        return original_decision

def main():
    # 파일 로드
    dataset_path = 'data/golden_dataset_2000_advanced.json'
    print(f"Loading dataset from {dataset_path}...")

    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cases = data['cases']
    print(f"Loaded {len(cases)} cases\n")

    # 통계 추적
    stats = {
        'total_cases': len(cases),
        'unchanged': 0,
        'block_to_approval': 0,
        'approval_to_block': 0,
        'other_changes': 0,
        'by_action_type': defaultdict(int),
        'decision_distribution_before': defaultdict(int),
        'decision_distribution_after': defaultdict(int),
    }

    # 변경 전 분포
    for case in cases:
        decision = case['expected_decision']
        stats['decision_distribution_before'][decision] += 1

    print("Decision distribution BEFORE:")
    for decision, count in sorted(stats['decision_distribution_before'].items()):
        print(f"  {decision}: {count}")
    print()

    # 케이스별 분석 및 수정
    changes_log = []

    for idx, case in enumerate(cases):
        prompt = case['prompt']
        original_decision = case['expected_decision']

        # 새 결정 결정
        new_decision = determine_decision(prompt, original_decision)

        # 액션 타입 추적
        action_type = analyze_prompt(prompt)
        stats['by_action_type'][action_type] += 1

        # 변경사항 추적
        if new_decision == original_decision:
            stats['unchanged'] += 1
        elif original_decision == 'block' and new_decision == 'approval':
            stats['block_to_approval'] += 1
            if stats['block_to_approval'] <= 10:  # 처음 10개만 로깅
                changes_log.append({
                    'case_id': case['case_id'],
                    'prompt': prompt[:50] + '...' if len(prompt) > 50 else prompt,
                    'rank': case['user_context']['rank'],
                    'sensitivity': case['sensitivity_level'],
                    'change': f"{original_decision} → {new_decision}"
                })
        elif original_decision == 'approval' and new_decision == 'block':
            stats['approval_to_block'] += 1
        else:
            stats['other_changes'] += 1

        # 케이스 업데이트
        case['expected_decision'] = new_decision
        stats['decision_distribution_after'][new_decision] += 1

    # 파일 저장
    print("Saving refined dataset...")
    with open(dataset_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved to {dataset_path}\n")

    # 통계 출력
    print("=" * 70)
    print("DATASET REFINEMENT STATISTICS")
    print("=" * 70)
    print(f"\nTotal cases processed: {stats['total_cases']}")
    print(f"Unchanged: {stats['unchanged']}")
    print(f"block → approval: {stats['block_to_approval']}")
    print(f"approval → block: {stats['approval_to_block']}")
    print(f"Other changes: {stats['other_changes']}")

    print("\n" + "-" * 70)
    print("ACTION TYPE DISTRIBUTION (during analysis):")
    print("-" * 70)
    for action_type in sorted(stats['by_action_type'].keys()):
        count = stats['by_action_type'][action_type]
        pct = (count / stats['total_cases']) * 100
        print(f"  {action_type}: {count} ({pct:.1f}%)")

    print("\n" + "-" * 70)
    print("Decision distribution BEFORE:")
    print("-" * 70)
    for decision in sorted(stats['decision_distribution_before'].keys()):
        count = stats['decision_distribution_before'][decision]
        pct = (count / stats['total_cases']) * 100
        print(f"  {decision}: {count} ({pct:.1f}%)")

    print("\n" + "-" * 70)
    print("Decision distribution AFTER:")
    print("-" * 70)
    for decision in sorted(stats['decision_distribution_after'].keys()):
        count = stats['decision_distribution_after'][decision]
        pct = (count / stats['total_cases']) * 100
        print(f"  {decision}: {count} ({pct:.1f}%)")

    print("\n" + "-" * 70)
    print("Sample of block → approval changes (first 10):")
    print("-" * 70)
    for change in changes_log[:10]:
        print(f"\n  Case: {change['case_id']}")
        print(f"    Prompt: {change['prompt']}")
        print(f"    Rank: {change['rank']}, Sensitivity: {change['sensitivity']}")
        print(f"    Change: {change['change']}")

    print("\n" + "=" * 70)
    print("Dataset refinement completed successfully!")
    print("=" * 70)

if __name__ == '__main__':
    main()
