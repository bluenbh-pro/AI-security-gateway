import json

# 예상 결정들의 고유값 확인
with open('data/golden_dataset_realistic_800.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

decisions = set()
for case in data['cases']:
    decisions.add(case['expected_decision'])

print('예상 결정(expected_decision)의 고유값:')
for d in sorted(decisions):
    print(f'  - {d}')

# 몇 개 예제 보기
print()
print('예제:')
for i in range(5):
    case = data['cases'][i]
    print(f'{i+1}. {case["expected_decision"]} (score: {case["expected_score_range"]})')
