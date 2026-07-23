#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Performance Benchmark for AI Security Gateway
응답시간, 메모리, 정확도 등 성능 지표 측정

사용법:
  python benchmark.py --dataset data/golden_dataset.json --output benchmark_results.json
"""

import json
import time
import psutil
import os
import sys
from typing import Dict, List, Any
from datetime import datetime
from dotenv import load_dotenv

# 모듈 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.orchestrator import GatewayOrchestrator

load_dotenv()


class SecurityGatewayBenchmark:
    """AI Security Gateway 벤치마크"""

    def __init__(self):
        """초기화"""
        self.results = []
        self.process = psutil.Process(os.getpid())
        self.orchestrator = GatewayOrchestrator()

    def measure_single_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        단일 케이스 성능 측정

        Returns:
            - response_time: 응답 시간 (초)
            - memory_used: 메모리 사용량 (MB)
            - risk_score: 위험도 점수
            - decision: 의사결정
            - accuracy: 정확도 (기대값과 비교)
        """
        case_id = test_case.get("case_id", "unknown")
        prompt = test_case.get("prompt", "")
        context = test_case.get("user_context", {})

        # 메모리 측정 시작
        mem_before = self.process.memory_info().rss / 1024 / 1024  # MB

        # 응답 시간 측정
        start_time = time.time()
        try:
            result = self.orchestrator.process_request(
                request_id=f"benchmark_{case_id}",
                prompt=prompt,
                user_context=context
            )
            response_time = time.time() - start_time

            # 메모리 측정 종료
            mem_after = self.process.memory_info().rss / 1024 / 1024  # MB
            memory_used = mem_after - mem_before

            # 정확도 계산
            expected_risk = test_case.get("expected_risk_score", None)
            actual_risk = result.final_score
            risk_accuracy = 100 - abs(actual_risk - expected_risk) if expected_risk else None

            expected_decision = test_case.get("expected_decision", None)
            actual_decision = result.final_decision
            decision_correct = actual_decision == expected_decision

            # Agent별 개별 점수 추출
            agent1_score = result.data_classification.get("risk_score", 0)
            agent2_score = result.context_risk_score
            agent3_score = result.policy_risk_score

            return {
                "case_id": case_id,
                "status": "success",
                "response_time": response_time,
                "memory_used": memory_used,
                # 최종 점수
                "risk_score": actual_risk,
                "decision": actual_decision,
                # Agent별 개별 점수
                "agent1_score": agent1_score,
                "agent2_score": agent2_score,
                "agent3_score": agent3_score,
                # 기대값
                "expected_risk": expected_risk,
                "expected_decision": expected_decision,
                "risk_accuracy": risk_accuracy,
                "decision_correct": decision_correct,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "case_id": case_id,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def run_benchmark(self, dataset_path: str, limit: int = None) -> List[Dict]:
        """
        벤치마크 실행

        Args:
            dataset_path: Golden Dataset 경로 (기본값: 최신 Rubric 버전)
            limit: 테스트할 최대 케이스 수

        Returns:
            결과 리스트
        """
        # 최신 버전 자동 선택: golden_dataset_final.json (Rubric V2 기반)
        import os
        if dataset_path == "data/golden_dataset.json" and os.path.exists("data/golden_dataset_final.json"):
            dataset_path = "data/golden_dataset_final.json"
            print(f"[BENCH] Using final Rubric V2 dataset: {dataset_path}")
        else:
            print(f"[BENCH] Starting benchmark: {dataset_path}")

        # 데이터 로드
        with open(dataset_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        test_cases = data.get("test_cases", [])
        if limit:
            test_cases = test_cases[:limit]

        print(f"[BENCH] Test cases: {len(test_cases)}\n")

        # 벤치마크 실행
        for i, case in enumerate(test_cases, 1):
            print(f"[{i}/{len(test_cases)}] Case {case.get('case_id')} 측정 중...", end=" ")

            result = self.measure_single_case(case)
            self.results.append(result)

            if result.get("status") == "success":
                print(f"[OK] {result['response_time']:.2f}s")
            else:
                print(f"[ERROR] {result.get('error', 'unknown')}")

        return self.results

    def generate_report(self) -> Dict[str, Any]:
        """벤치마크 리포트 생성"""
        successful = [r for r in self.results if r.get("status") == "success"]

        if not successful:
            return {"error": "No successful measurements"}

        # 응답 시간 분석
        response_times = [r["response_time"] for r in successful]
        memory_usage = [r["memory_used"] for r in successful if r.get("memory_used") is not None]

        # 정확도 분석
        decision_accuracy = sum(1 for r in successful if r.get("decision_correct")) / len(successful) * 100

        report = {
            "summary": {
                "total_cases": len(self.results),
                "successful": len(successful),
                "failed": len(self.results) - len(successful),
                "success_rate": f"{len(successful) / len(self.results) * 100:.1f}%"
            },
            "response_time": {
                "unit": "seconds",
                "min": min(response_times),
                "max": max(response_times),
                "mean": sum(response_times) / len(response_times),
                "median": sorted(response_times)[len(response_times) // 2],
                "p95": sorted(response_times)[int(len(response_times) * 0.95)],
                "p99": sorted(response_times)[int(len(response_times) * 0.99)]
            },
            "memory_usage": {
                "unit": "MB",
                "min": min(memory_usage) if memory_usage else None,
                "max": max(memory_usage) if memory_usage else None,
                "mean": sum(memory_usage) / len(memory_usage) if memory_usage else None
            },
            "accuracy": {
                "decision_accuracy": f"{decision_accuracy:.1f}%",
                "risk_score_mae": self._calculate_mae(successful)
            },
            "decision_distribution": self._get_decision_distribution(successful),
            "performance_targets": {
                "response_time_target": "< 2 seconds",
                "response_time_status": "[PASS]" if sum(1 for t in response_times if t < 2) / len(response_times) > 0.95 else "[FAIL]",
                "decision_accuracy_target": "> 90%",
                "decision_accuracy_status": "[PASS]" if decision_accuracy > 90 else "[WARN]" if decision_accuracy > 80 else "[FAIL]"
            }
        }

        return report

    def _calculate_mae(self, results: List[Dict]) -> float:
        """Mean Absolute Error 계산"""
        cases_with_expected = [r for r in results if r.get("expected_risk") is not None]

        if not cases_with_expected:
            return 0

        mae = sum(
            abs(r["risk_score"] - r["expected_risk"])
            for r in cases_with_expected
        ) / len(cases_with_expected)

        return round(mae, 2)

    def _get_decision_distribution(self, results: List[Dict]) -> Dict[str, int]:
        """의사결정 분포"""
        distribution = {}

        for result in results:
            decision = result.get("decision", "unknown")
            distribution[decision] = distribution.get(decision, 0) + 1

        return distribution

    def save_report(self, output_path: str) -> None:
        """리포트 저장"""
        report = self.generate_report()

        output_data = {
            "benchmark_date": datetime.now().isoformat(),
            "report": report,
            "detailed_results": self.results
        }

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"\n[OK] 벤치마크 리포트 저장: {output_path}")


def print_report(report: Dict) -> None:
    """리포트 콘솔 출력"""
    print("\n" + "=" * 70)
    print("[REPORT] BENCHMARK REPORT - AI Security Gateway")
    print("=" * 70)

    # Summary
    summary = report.get("summary", {})
    print(f"\n[SUMMARY]")
    print(f"  Total Cases: {summary.get('total_cases')}")
    print(f"  Successful: {summary.get('successful')}")
    print(f"  Success Rate: {summary.get('success_rate')}")

    # Response Time
    rt = report.get("response_time", {})
    print(f"\n[RESPONSE_TIME] (seconds)")
    print(f"  Min: {rt.get('min'):.3f}s")
    print(f"  Max: {rt.get('max'):.3f}s")
    print(f"  Mean: {rt.get('mean'):.3f}s")
    print(f"  P95: {rt.get('p95'):.3f}s")
    print(f"  P99: {rt.get('p99'):.3f}s")

    # Accuracy
    acc = report.get("accuracy", {})
    print(f"\n[ACCURACY]")
    print(f"  Decision Accuracy: {acc.get('decision_accuracy')}")
    print(f"  Risk Score MAE: {acc.get('risk_score_mae')}")

    # Targets
    targets = report.get("performance_targets", {})
    print(f"\n[TARGETS]")
    print(f"  Response Time: {targets.get('response_time_target')} - {targets.get('response_time_status')}")
    print(f"  Decision Accuracy: {targets.get('decision_accuracy_target')} - {targets.get('decision_accuracy_status')}")

    # Decision Distribution
    dist = report.get("decision_distribution", {})
    print(f"\n[DISTRIBUTION]")
    for decision, count in dist.items():
        print(f"  {decision}: {count}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI Security Gateway Benchmark")
    parser.add_argument("--dataset", default="data/golden_dataset.json", help="Golden Dataset 경로")
    parser.add_argument("--output", default="evaluation/benchmark_results.json", help="결과 저장 경로")
    parser.add_argument("--limit", type=int, help="테스트할 최대 케이스 수")

    args = parser.parse_args()

    # 벤치마크 실행
    benchmark = SecurityGatewayBenchmark()
    benchmark.run_benchmark(args.dataset, limit=args.limit)
    benchmark.save_report(args.output)

    # 리포트 출력
    report = benchmark.generate_report()
    print_report(report)
