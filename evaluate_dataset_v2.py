"""
Orchestrator를 새 데이터셋(412 cases)으로 평가

데이터: data/golden_dataset_realistic_800.json
출력: results/evaluation_dataset_v2.json
"""

import json
import sys
import os
from pathlib import Path
from tqdm import tqdm
from datetime import datetime

# Add core directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

from orchestrator import GatewayOrchestrator


def load_dataset(filepath: str) -> dict:
    """데이터셋 로드"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def evaluate_orchestrator(dataset: dict, output_dir: str = "results"):
    """Orchestrator 평가"""
    print("="*80)
    print("[Orchestrator 평가] 새 데이터셋 (412 cases)")
    print("="*80)

    orch = GatewayOrchestrator(a1_weight=0.6, a2_weight=0.3, a3_weight=0.05, a5_weight=0.05)

    cases = dataset['cases']
    print(f"\n[데이터셋] 총 {len(cases)}개 케이스 로드")

    results = []
    correct = 0
    decision_accuracy = {"Allow": [], "Conditional": [], "Approval": [], "Block": []}
    a1_grades_found = set()

    print(f"\n[평가 중...]")
    for i, case in tqdm(enumerate(cases), total=len(cases)):
        prompt = case['prompt']
        user_context = case['user_context']
        expected_decision = case['expected_decision']
        a1_expected_grade = case['a1_expected_grade']

        # Orchestrator 실행
        try:
            orch_result = orch.process_request(
                request_id=case['case_id'],
                prompt=prompt,
                user_context=user_context
            )

            is_correct = orch_result.final_decision == expected_decision
            correct += is_correct

            decision_accuracy[expected_decision].append(1 if is_correct else 0)
            a1_grades_found.add(a1_expected_grade)

            result = {
                "case_id": case['case_id'],
                "expected_decision": expected_decision,
                "predicted_decision": orch_result.final_decision,
                "correct": is_correct,
                "expected_score": case['expected_score'],
                "final_score": orch_result.final_score,
                "a1_data_sensitivity": orch_result.a1_data_sensitivity,
                "context_risk_score": orch_result.context_risk_score,
                "a3_violation_severity": orch_result.a3_violation_severity,
                "attack_score": orch_result.attack_score,
                "a1_expected_grade": a1_expected_grade,
                "department": user_context.get("department", ""),
                "rank": user_context.get("rank", ""),
            }
            results.append(result)
        except Exception as e:
            print(f"\n  [ERROR] {case['case_id']}: {str(e)}")
            continue

    # 평가 통계
    total = len(results)
    accuracy = correct / total * 100 if total > 0 else 0.0

    print(f"\n{'='*80}")
    print(f"[평가 완료]")
    print(f"{'='*80}")
    print(f"총 평가 케이스: {total}")
    print(f"정확도: {correct}/{total} = {accuracy:.2f}%")
    print(f"\n[의사결정별 정확도]")
    for decision, scores in decision_accuracy.items():
        if scores:
            decision_acc = sum(scores) / len(scores) * 100
            print(f"  {decision}: {sum(scores)}/{len(scores)} = {decision_acc:.2f}%")

    print(f"\n[A1 등급 커버리지]")
    print(f"  감지된 등급: {len(a1_grades_found)}/7개")
    for grade in sorted(a1_grades_found):
        print(f"    - {grade}")

    # 메트릭스 저장
    os.makedirs(output_dir, exist_ok=True)

    metrics = {
        "evaluation_date": datetime.now().isoformat(),
        "total_cases": total,
        "accuracy": accuracy,
        "correct": correct,
        "decision_accuracy": {
            decision: {
                "correct": sum(scores),
                "total": len(scores),
                "accuracy": sum(scores) / len(scores) * 100 if scores else 0
            }
            for decision, scores in decision_accuracy.items()
        },
        "a1_grades_found": sorted(list(a1_grades_found)),
        "a1_grades_coverage": len(a1_grades_found) / 7 * 100,
    }

    # 결과 저장
    output_file = os.path.join(output_dir, "evaluation_dataset_v2.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "metrics": metrics,
            "results": results
        }, f, indent=2, ensure_ascii=False)

    metrics_file = os.path.join(output_dir, "metrics_dataset_v2.json")
    with open(metrics_file, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] 결과 저장:")
    print(f"  - {output_file}")
    print(f"  - {metrics_file}")

    return metrics, results, orch


if __name__ == "__main__":
    # 데이터셋 로드
    dataset_path = "data/golden_dataset_realistic_800.json"
    if not os.path.exists(dataset_path):
        print(f"[ERROR] {dataset_path} 파일을 찾을 수 없습니다.")
        sys.exit(1)

    dataset = load_dataset(dataset_path)

    # 평가
    metrics, results, orch = evaluate_orchestrator(dataset)

    # 요약 통계
    print(f"\n{'='*80}")
    print(f"[요약]")
    print(f"{'='*80}")
    print(f"모델 정확도: {metrics['accuracy']:.2f}%")
    print(f"A1 등급 커버리지: {metrics['a1_grades_coverage']:.1f}%")

    # 캐시 통계
    if orch and orch.cache:
        orch.cache.print_stats()
