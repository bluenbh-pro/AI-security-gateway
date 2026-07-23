#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
평가 완료 후 자동으로 보고서를 생성하는 스크립트
"""

import os
import time
import subprocess
import json

def wait_for_evaluation(timeout=3600):
    """평가 완료 대기"""
    result_file = 'results/evaluation_p1_v4_final.json'
    start_time = time.time()

    print("[Monitor] 평가 완료 대기 중...")
    while time.time() - start_time < timeout:
        if os.path.exists(result_file):
            # 파일이 있는지 확인하고, 크기가 변하지 않는지 확인
            size1 = os.path.getsize(result_file)
            time.sleep(2)
            size2 = os.path.getsize(result_file)

            if size1 == size2 and size1 > 1000:  # 파일이 안정화됨
                print(f"\n✓ 평가 완료 감지: {result_file}")
                return True

        time.sleep(5)

    print(f"\n✗ 타임아웃: {timeout}초 내 평가 완료 없음")
    return False

def run_report_generation():
    """보고서 생성"""
    print("\n[Report] 최종 보고서 생성 중...")

    try:
        subprocess.run(['python', 'generate_final_report.py'], check=True)
        print("\n✓ 최종 보고서 생성 완료")
    except subprocess.CalledProcessError as e:
        print(f"\n✗ 보고서 생성 실패: {e}")
        return False

    return True

def run_comparison_analysis():
    """비교 분석"""
    print("\n[Analysis] 성능 비교 분석 중...")

    try:
        subprocess.run(['python', 'analyze_p1_v4_comparison.py'], check=True)
        print("\n✓ 성능 비교 분석 완료")
    except subprocess.CalledProcessError as e:
        print(f"\n✗ 비교 분석 실패: {e}")
        return False

    return True

def main():
    print("=" * 80)
    print("[P1 평가 완료 모니터링]")
    print("=" * 80)

    # 평가 완료 대기
    if not wait_for_evaluation():
        print("\n평가 완료 타임아웃. 수동으로 진행하세요.")
        return

    # 평가 결과 확인
    try:
        with open('results/evaluation_p1_v4_final.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"\n평가된 케이스: {data.get('total_cases', 'N/A')}개")
            print(f"소요 시간: {data.get('elapsed_seconds', 'N/A')}초")
    except Exception as e:
        print(f"결과 확인 실패: {e}")

    # 보고서 생성
    if not run_report_generation():
        return

    # 비교 분석
    run_comparison_analysis()

    print("\n" + "=" * 80)
    print("[완료]")
    print("=" * 80)
    print("\n생성된 파일:")
    print("  - results/evaluation_p1_v4_final.json (평가 결과)")
    print("  - results/metrics_p1_v4_final.json (메트릭)")
    print("  - results/P1_FINAL_REPORT.md (최종 보고서)")

if __name__ == '__main__':
    main()
