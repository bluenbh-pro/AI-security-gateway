#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json

with open('data/golden_dataset_large_v7_enhanced_agent5.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

non_attack = [c for c in data['test_cases'] if not c.get('attack_detected')]
approval_cases = [c for c in non_attack if 50 <= c.get('orchestrator_score', 0) < 76]

samples = []
for lower in [50, 55, 60, 65, 70]:
    case = next((c for c in approval_cases if lower <= c.get('orchestrator_score', 0) < lower+5), None)
    if case:
        samples.append(case)

result = {'samples': []}
for i, case in enumerate(samples, 1):
    data_class = case.get('data_classification', {})
    result['samples'].append({
        'case': i,
        'final_score': round(case.get('orchestrator_score', 0), 2),
        'agent1_risk_score': round(data_class.get('risk_score', 0), 2),  # Agent 1 점수
        'agent1_sensitivity': data_class.get('sensitivity_level', ''),
        'agent2_context_risk': round(case.get('context_risk_score', 0), 1),
        'data_types': data_class.get('data_types', []),
        'agent3_laws': case.get('applicable_laws', []),
        'prompt': case.get('prompt', '')
    })

with open('approval_5cases_full.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print('Done')
