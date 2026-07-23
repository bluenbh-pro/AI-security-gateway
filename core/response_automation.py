"""
자동 대응 실행 모듈

역할: 의사결정에 따라 자동 응답 생성 및 실행

기능:
- 마스킹: 민감 데이터 자동 처리 (정규식 기반)
- 로깅: 감사 추적 기록 (JSON 형식)
- 응답: 의사결정별 응답 생성 (허용/마스킹/승인요청/차단)
- 알림: 위험 이벤트 알림 (W4 구현)

구현 상태: ✅ W2 완료 (기본 기능)
"""

from typing import Dict, Any
from datetime import datetime


class ResponseAutomation:
    """의사결정에 따른 자동 대응 실행"""

    def __init__(self, log_path: str = "logs/security_events.log"):
        """
        초기화

        Args:
            log_path: 감사 로그 파일 경로
        """
        self.log_path = log_path

    def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        의사결정에 따른 응답 실행

        의사결정별 응답:
        1. 허용 (allow): 원본 입력 그대로 통과
        2. 조건부허용 (conditional): 경고 메시지와 함께 통과
        3. 마스킹 (mask): 민감 데이터 자동 마스킹
        4. 승인요청 (approval_request): 관리자 승인 요청
        5. 차단 (block): 입력 차단

        입력: {
            "decision": "마스킹",
            "user_input": "고객 박철수의 계좌번호는 1234567890입니다",
            "masking_rules": ["계좌번호"],
            "user_id": "user_001",
            "risk_score": 55
        }

        출력: {
            "action": "mask",
            "output": "고객 박철수의 계좌번호는 ****입니다",
            "logged": true
        }
        """
        decision = state.get("action", "allow")

        # 의사결정별 응답 실행
        if decision == "allow":
            output = self._execute_allow(state)
        elif decision == "conditional":
            output = self._execute_conditional(state)
        elif decision == "mask":
            output = self._execute_mask(
                state.get("user_input", ""),
                state.get("masking_rules", [])
            )
        elif decision == "approval_request":
            output = self._execute_approval_request(state)
        elif decision == "block":
            output = self._execute_block(state)
        else:
            output = state.get("user_input", "")

        # 로깅
        logged = self._log_event({
            "timestamp": datetime.now().isoformat(),
            "user_id": state.get("user_id", "unknown"),
            "decision": state.get("decision", "unknown"),
            "risk_score": state.get("risk_score", 0),
            "action": decision
        })

        return {
            "action": decision,
            "output": output,
            "logged": logged
        }

    def _execute_allow(self, state: Dict[str, Any]) -> str:
        """허용: 원본 입력 그대로 통과"""
        return state.get("user_input", "")

    def _execute_conditional(self, state: Dict[str, Any]) -> str:
        """조건부허용: 경고 메시지와 함께 통과"""
        warning = "[⚠️ 주의] 이 요청은 정책상 주의 항목을 포함하고 있습니다. 승인자의 검토가 권장됩니다."
        return f"{warning}\n\n{state.get('user_input', '')}"

    def _execute_mask(self, user_input: str, masking_rules: list) -> str:
        """마스킹: 민감 데이터 자동 처리"""
        masked_text = user_input

        for rule in masking_rules:
            masked_text = self._apply_masking(masked_text, rule)

        return masked_text

    def _execute_approval_request(self, state: Dict[str, Any]) -> str:
        """승인요청: 관리자에게 승인 요청 (메일/메시지 등)"""
        approval_msg = f"[⏳ 승인 대기 중] 위험도: {state.get('risk_score', 0):.1f}/100\n요청 ID: {state.get('user_id', 'unknown')}"
        return approval_msg

    def _execute_block(self, state: Dict[str, Any]) -> str:
        """차단: 사용자 입력 차단 및 로깅"""
        block_msg = f"[❌ 차단됨] 이 요청은 보안 정책 위반으로 차단되었습니다. (위험도: {state.get('risk_score', 0):.1f}/100)"
        return block_msg

    def _log_event(self, event: Dict[str, Any]) -> bool:
        """
        감사 추적 로깅

        로그 포맷:
        timestamp|user_id|decision|risk_score|action
        """
        try:
            import json
            log_entry = json.dumps(event, ensure_ascii=False) + "\n"

            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(log_entry)

            return True
        except Exception as e:
            print(f"[로깅 오류] {e}")
            return False

    def _apply_masking(self, text: str, rule: str) -> str:
        """
        마스킹 규칙 적용

        규칙 예시:
        - 주민번호: "123456-7890123" → "123456-****"
        - 계좌번호: "1234567890" → "****"
        - 이메일: "user@example.com" → "u***@example.com"
        """
        import re

        masking_patterns = {
            "주민번호": (r"\d{6}-\d{7}", "***-****"),
            "계좌번호": (r"\d{10,20}", "****"),
            "신용카드": (r"\d{4}-?\d{4}-?\d{4}-?\d{4}", "****-****-****-****"),
            "이메일": (r"\w+@\w+\.\w+", lambda m: m.group(0)[0] + "***" + m.group(0)[-4:]),
            "전화번호": (r"\d{2,3}-?\d{3,4}-?\d{4}", "***-****-****"),
        }

        if rule in masking_patterns:
            pattern, replacement = masking_patterns[rule]
            text = re.sub(pattern, replacement, text)

        return text

    def _send_notification(self, event: Dict[str, Any]) -> bool:
        """
        위험 이벤트 알림 (관리자 메일/Slack 등)

        [W4에서 구현] 현재는 placeholder
        """
        return True


# ============================================================================
# 사용 예제
# ============================================================================

if __name__ == "__main__":
    automator = ResponseAutomation()

    test_state = {
        "decision": "마스킹",
        "user_input": "고객 박철수의 계좌번호는 1234567890입니다",
        "masking_rules": ["계좌번호"],
        "user_id": "user_001",
        "risk_score": 55
    }

    result = automator.execute(test_state)
    print(result)
