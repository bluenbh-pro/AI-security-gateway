import json

# 처음 몇 개 케이스의 상세 결과 확인
with open('results/evaluation_results.json', 'r', encoding='utf-8') as f:
    results = json.load(f)

print('처음 10개 케이스 상세 결과:')
print('=' * 100)
for i in range(min(10, len(results))):
    r = results[i]
    print(f'{i+1}. {r["case_id"][:50]}...')
    print(f'   Expected: {r["expected_decision"]:20s} Score: {r["expected_score_range"]}')
    print(f'   Final:    {r["final_decision"]:20s} Score: {r["final_score"]:.1f}')
    print(f'   Match: {r["match"]}')
    print(f'   Explanation: {r["explanation"]}')
    print()
