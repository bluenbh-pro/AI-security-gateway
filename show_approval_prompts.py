#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Approval Required 케이스의 실제 프롬프트 표시"""

import json

with open('data/golden_dataset_large_v7_enhanced_agent5.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

test_cases = data['test_cases']
non_attack = [c for c in test_cases if not c.get('attack_detected')]
approval_cases = [c for c in non_attack if 50 <= c.get('orchestrator_score', 0) < 76]

# 5개 샘플 추출
samples = []
for lower in [50, 55, 60, 65, 70]:
    case = next((c for c in approval_cases if lower <= c.get('orchestrator_score', 0) < lower+5), None)
    if case:
        samples.append(case)

print("="*120)
print("Approval Required (50-75) Cases - Actual Prompts")
print("="*120)

for i, case in enumerate(samples, 1):
    score = case.get('orchestrator_score', 0)
    context_risk = case.get('context_risk_score', 0)
    data_types = case.get('data_classification', {}).get('data_types', [])
    laws = case.get('applicable_laws', [])
    prompt = case.get('prompt', '')

    print(f"\n[케이스 {i}]")
    print(f"점수: {score:.2f}")
    print(f"컨텍스트위험도(A2): {context_risk:.1f}")
    print(f"데이터타입: {data_types}")
    print(f"적용법령: {laws if laws else '없음'}")
    print(f"프롬프트:")
    print(f"  {prompt}")
    print("-" * 120)

print("\n" + "="*120)
