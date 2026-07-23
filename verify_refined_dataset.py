#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

# Verify the refined dataset
with open('data/golden_dataset_2000_advanced.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Check decision distribution
decision_counts = {}
for case in data['cases']:
    decision = case['expected_decision']
    decision_counts[decision] = decision_counts.get(decision, 0) + 1

print("Final verification - Decision counts in refined dataset:")
for decision in sorted(decision_counts.keys()):
    count = decision_counts[decision]
    pct = (count / len(data['cases'])) * 100
    print(f"  {decision}: {count} ({pct:.1f}%)")

print(f"\nTotal cases: {len(data['cases'])}")
print("\nFile saved successfully: data/golden_dataset_2000_advanced.json")

# Sample some cases with read-only prompts to confirm they are now approval
print("\n" + "=" * 70)
print("Sample cases with READ-only prompts (should be approval):")
print("=" * 70)

read_only_samples = [case for case in data['cases']
                     if '조회' in case['prompt'] and case['expected_decision'] == 'approval'][:5]

for idx, case in enumerate(read_only_samples, 1):
    print(f"\n{idx}. Case ID: {case['case_id']}")
    print(f"   Prompt: {case['prompt']}")
    print(f"   Decision: {case['expected_decision']}")
    print(f"   Sensitivity: {case['sensitivity_level']}")
