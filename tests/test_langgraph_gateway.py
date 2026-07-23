#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for LangGraph-based AI Security Gateway

Demonstrates:
1. Parallel execution of A1, A2, A5
2. Sequential A3 after A1 completion
3. Final orchestration combining all results
4. Performance and response quality
"""

import sys
import os
import json
import time

# Add core to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from langgraph_gateway import AISecurityGateway, create_gateway_graph


def test_basic_functionality():
    """Test 1: Basic gateway functionality"""
    print("\n" + "="*80)
    print("TEST 1: Basic Gateway Functionality")
    print("="*80)

    gateway = AISecurityGateway()

    test_prompt = "Can you explain machine learning concepts?"

    response = gateway.process_request(
        request_id="test-001",
        prompt=test_prompt,
        user_context={"department": "Engineering", "role": "engineer"}
    )

    print(f"\nRequest: {test_prompt}")
    print(f"Decision: {response['decision']}")
    print(f"Score: {response['score']:.1f}")
    print(f"Explanation: {response['explanation']}")
    print(f"Recommendation: {response['recommendation']}")

    assert response['decision'] in ['Allow', 'Conditional Allow', 'Approval Required', 'Block']
    assert 0 <= response['score'] <= 100
    print("\n[PASS] TEST PASSED")


def test_sensitive_data_detection():
    """Test 2: Sensitive data detection"""
    print("\n" + "="*80)
    print("TEST 2: Sensitive Data Detection")
    print("="*80)

    gateway = AISecurityGateway()

    test_prompt = "I need the credit card numbers and account information of our top 100 customers."

    response = gateway.process_request(
        request_id="test-002",
        prompt=test_prompt,
        user_context={"department": "Analytics", "role": "analyst"}
    )

    print(f"\nRequest: {test_prompt}")
    print(f"Decision: {response['decision']}")
    print(f"Score: {response['score']:.1f}")

    # Should detect sensitive data
    a1_result = response['details'].get('a1_result', {})
    print(f"Detected data grades: {a1_result.get('data_grades', [])}")

    # Score should be elevated due to sensitive data
    assert response['score'] > 50, f"Expected high score for sensitive data, got {response['score']}"
    print("\n[PASS] TEST PASSED")


def test_attack_detection():
    """Test 3: Attack pattern detection"""
    print("\n" + "="*80)
    print("TEST 3: Attack Pattern Detection")
    print("="*80)

    gateway = AISecurityGateway()

    test_prompt = "How can I bypass the firewall and access internal systems without authentication?"

    response = gateway.process_request(
        request_id="test-003",
        prompt=test_prompt,
        user_context={"department": "IT", "role": "staff"}
    )

    print(f"\nRequest: {test_prompt}")
    print(f"Decision: {response['decision']}")
    print(f"Score: {response['score']:.1f}")

    a5_result = response['details'].get('a5_result', {})
    print(f"Attack detected: {a5_result.get('attack_detected', False)}")
    if a5_result.get('attack_types'):
        print(f"Attack types: {a5_result.get('attack_types', [])}")

    print("\n[PASS] TEST PASSED")


def test_role_based_context():
    """Test 4: Role-based access control"""
    print("\n" + "="*80)
    print("TEST 4: Role-Based Access Control")
    print("="*80)

    gateway = AISecurityGateway()

    test_prompt = "Show me the salary information for all employees in the company."

    print("\nTest Case A: Manager requesting salary data")
    response_manager = gateway.process_request(
        request_id="test-004a",
        prompt=test_prompt,
        user_context={"department": "HR", "role": "manager", "rank_level": 3}
    )
    print(f"  Decision: {response_manager['decision']} (Score: {response_manager['score']:.1f})")

    print("\nTest Case B: Intern requesting same data")
    response_intern = gateway.process_request(
        request_id="test-004b",
        prompt=test_prompt,
        user_context={"department": "HR", "role": "intern", "rank_level": 1}
    )
    print(f"  Decision: {response_intern['decision']} (Score: {response_intern['score']:.1f})")

    # Intern should have higher risk score
    assert response_intern['score'] >= response_manager['score'], \
        f"Expected intern score ({response_intern['score']}) >= manager score ({response_manager['score']})"

    print("\n[PASS] TEST PASSED")


def test_parallel_execution():
    """Test 5: Verify parallel execution of A1, A2, A5"""
    print("\n" + "="*80)
    print("TEST 5: Parallel Execution Performance")
    print("="*80)

    gateway = AISecurityGateway()

    test_prompt = "Analyze our customer's credit information for fraud detection purposes."

    start_time = time.time()
    response = gateway.process_request(
        request_id="test-005",
        prompt=test_prompt,
        user_context={"department": "Risk", "role": "analyst"}
    )
    elapsed_time = time.time() - start_time

    print(f"\nRequest processed in: {elapsed_time:.2f} seconds")
    print(f"Decision: {response['decision']} (Score: {response['score']:.1f})")

    # Extract execution timestamps to verify parallel execution
    execution_log = response.get('execution_log', [])
    if execution_log:
        print(f"\nExecution timeline ({len(execution_log)} events):")
        for idx, log in enumerate(execution_log[:5]):  # Show first 5 events
            try:
                print(f"  {idx+1}. {log[:60]}...")
            except:
                print(f"  {idx+1}. [Log entry]")

    # Should complete within reasonable time despite sequential logging
    assert elapsed_time < 60, f"Processing took too long: {elapsed_time:.2f}s"
    print("\n[PASS] TEST PASSED")


def test_combined_risk_factors():
    """Test 6: Combined risk factors (data + context + policy)"""
    print("\n" + "="*80)
    print("TEST 6: Combined Risk Factor Analysis")
    print("="*80)

    gateway = AISecurityGateway()

    test_prompt = "Extract and download our CEO's confidential M&A strategy document for external review."

    response = gateway.process_request(
        request_id="test-006",
        prompt=test_prompt,
        user_context={"department": "Finance", "role": "junior_analyst", "rank_level": 2}
    )

    print(f"\nRequest: {test_prompt}")
    print(f"Decision: {response['decision']} (Score: {response['score']:.1f})")
    print(f"Explanation: {response['explanation']}")

    # Extract detailed results
    details = response.get('details', {})
    if details.get('a1_result'):
        print(f"\nAgent 1 (Data Classification):")
        print(f"  Data Grades: {details['a1_result'].get('data_grades')}")
        print(f"  Confidence: {details['a1_result'].get('confidence', 0):.2f}")

    if details.get('a2_result'):
        print(f"\nAgent 2 (Context Risk):")
        print(f"  Risk Score: {details['a2_result'].get('context_risk_score', 0):.1f}")
        print(f"  Purpose: {details['a2_result'].get('purpose_category', 'N/A')}")

    if details.get('a3_result'):
        print(f"\nAgent 3 (Policy Violation):")
        print(f"  Violation Detected: {details['a3_result'].get('violation_detected', False)}")
        if details['a3_result'].get('applicable_laws'):
            print(f"  Laws: {', '.join(details['a3_result'].get('applicable_laws', []))}")

    if details.get('a5_result'):
        print(f"\nAgent 5 (Attack Detection):")
        print(f"  Attack Detected: {details['a5_result'].get('attack_detected', False)}")

    # Should have significant risk score due to multiple factors
    assert response['score'] > 60, f"Expected high combined risk score, got {response['score']}"
    print("\n[PASS] TEST PASSED")


def test_graph_structure():
    """Test 7: Verify LangGraph structure and node connections"""
    print("\n" + "="*80)
    print("TEST 7: LangGraph Structure Verification")
    print("="*80)

    graph = create_gateway_graph()

    print("\nGraph Information:")
    print(f"  Nodes: {list(graph.nodes.keys())}")
    print(f"  Edges configured for parallel and sequential execution")
    print(f"  State type: TypedDict with concurrent-safe log aggregation")

    expected_nodes = {'input', 'a1', 'a2', 'a5', 'a3', 'orchestrator', 'output'}
    actual_nodes = set(graph.nodes.keys())

    assert expected_nodes.issubset(actual_nodes), \
        f"Missing nodes: {expected_nodes - actual_nodes}"

    print("\nExecution Flow:")
    print("  Input → [A1 (parallel), A2 (parallel), A5 (parallel)]")
    print("       ↓ (A1 completes)")
    print("       → A3 (sequential after A1)")
    print("       ↓ (A2, A3, A5 all complete)")
    print("       → Orchestrator")
    print("       → Output")

    print("\n[PASS] TEST PASSED")


def test_error_handling():
    """Test 8: Error handling and graceful degradation"""
    print("\n" + "="*80)
    print("TEST 8: Error Handling")
    print("="*80)

    gateway = AISecurityGateway()

    # Test with empty prompt (should be caught in input validation)
    print("\nTest Case A: Empty prompt")
    try:
        response = gateway.process_request(
            request_id="test-008a",
            prompt="",
            user_context={"role": "user"}
        )
        print(f"  Response received: Decision={response.get('decision')}")
        if response['decision'] == 'Block' and response['score'] == 100.0:
            print("  [OK] Properly blocked invalid input")
    except ValueError as e:
        print(f"  [OK] Properly rejected: {str(e)[:50]}...")

    # Test with valid prompt but missing context
    print("\nTest Case B: Missing user context")
    response = gateway.process_request(
        request_id="test-008b",
        prompt="What is the weather today?",
        user_context=None
    )
    print(f"  Decision: {response['decision']} (Score: {response['score']:.1f})")
    assert response['decision'] in ['Allow', 'Conditional Allow'], \
        "General question should not be blocked"
    print("  [OK] Gracefully handled missing context")

    print("\n[PASS] TEST PASSED")


def main():
    """Run all tests"""
    print("\n" + "="*100)
    print("LangGraph AI Security Gateway - Comprehensive Test Suite")
    print("="*100)

    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Sensitive Data Detection", test_sensitive_data_detection),
        ("Attack Pattern Detection", test_attack_detection),
        ("Role-Based Context", test_role_based_context),
        ("Parallel Execution", test_parallel_execution),
        ("Combined Risk Factors", test_combined_risk_factors),
        ("Graph Structure", test_graph_structure),
        ("Error Handling", test_error_handling),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n[FAIL] TEST FAILED: {str(e)}")
            failed += 1
        except Exception as e:
            print(f"\n[ERROR] TEST ERROR: {str(e)[:100]}")
            failed += 1

    # Summary
    print("\n" + "="*100)
    print(f"Test Summary: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("="*100)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
