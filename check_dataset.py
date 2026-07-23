import json
with open('data/golden_dataset_realistic_800.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('메타데이터:')
print(f'  total_cases: {data["metadata"]["total_cases"]}')
print()

print('케이스 구조 (첫 1개):')
case = data['cases'][0]
print(f'  keys: {list(case.keys())}')
for key in case.keys():
    value = case[key]
    if isinstance(value, dict):
        print(f'  {key}: {list(value.keys())}')
    elif isinstance(value, list):
        if len(str(value)) > 100:
            print(f'  {key}: [{len(value)} items]')
        else:
            print(f'  {key}: {value}')
    else:
        val_str = str(value)[:100] if len(str(value)) > 100 else str(value)
        print(f'  {key}: {type(value).__name__} = {val_str}')

print()
print('첫 케이스 상세:')
print(json.dumps(case, ensure_ascii=False, indent=2)[:1500])
