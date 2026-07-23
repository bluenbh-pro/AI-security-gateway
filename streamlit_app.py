#!/usr/bin/env python3
"""
Streamlit UI for AI Gateway Orchestrator
- 샘플 프롬프트 입력
- Agent별 점수/의사결정 표시
- Voting system 시각화
- 최종 결정 표시
"""

import streamlit as st
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

from orchestrator import GatewayOrchestrator

# ═════════════════════════════════════════════════════════════════════
# Helper 함수들
# ═════════════════════════════════════════════════════════════════════

def _get_dept_appropriateness_desc(context_risk: float, dept_score: float, user_context: dict) -> str:
    """부서 적절성 점수 설명"""
    if dept_score > 80:
        return "✅ 부서의 업무 범위와 완벽히 일치"
    elif dept_score > 60:
        return "✅ 부서의 업무 범위 내이나 추가 확인 권장"
    elif dept_score > 40:
        return "⚠️ 부서 권한이 다소 미흡함"
    else:
        return "❌ 부서 권한 부족: 데이터 접근 불가능"

def _get_role_credibility_desc(role_score: float) -> str:
    """역할 신뢰도 점수 설명"""
    if role_score >= 95:
        return "임원급: 최고 신뢰도, 광범위한 권한"
    elif role_score >= 80:
        return "파트장급: 높은 신뢰도, 제한된 권한"
    elif role_score >= 50:
        return "프로급: 중간 신뢰도, 업무 관련 범위만"
    else:
        return "외주인력: 낮은 신뢰도, 최소 권한만"

def _get_decision_reason(
    decision: str,
    a1_score: float,
    a2_score: float,
    a3_score: float,
    a5_score: float,
    a1_dec: str,
    a2_dec: str,
    a3_dec: str,
    a5_dec: str
) -> str:
    """최종 의사결정 이유 설명"""
    # 점수가 높은 Agent부터 찾기
    agents = [
        ("A1 데이터 민감도", a1_score, a1_dec),
        ("A2 컨텍스트 위험도", a2_score, a2_dec),
        ("A3 정책 위반", a3_score, a3_dec),
        ("A5 공격 탐지", a5_score, a5_dec),
    ]
    agents_sorted = sorted(agents, key=lambda x: x[1], reverse=True)

    if decision == "Block":
        # Block을 유도한 Agent 찾기
        for name, score, dec in agents_sorted:
            if dec == "Block":
                if "A1" in name and score > 80:
                    return f"A1 데이터 극민감도 ({score:.0f}점) - 고유식별정보/극비 데이터 포함"
                elif "A2" in name:
                    return f"A2 부서권한 부족 ({score:.0f}점) - 해당 부서는 이 데이터 접근 불가"
                elif "A3" in name:
                    return f"A3 정책 위반 ({score:.0f}점) - 법규 위반 우려"
                elif "A5" in name:
                    return f"A5 공격 탐지 ({score:.0f}점) - 보안 위협 패턴 감지"

        # 기본 값
        return f"높은 보안 위험도 (점수: {max(a1_score, a2_score, a3_score, a5_score):.0f})"

    elif decision == "Approval":
        # Approval을 유도한 Agent들
        high_agents = [n for n, s, d in agents_sorted if s > 50 and d in ["Approval", "Block"]]
        if high_agents:
            return f"{high_agents[0]} 점수 상승 (추가 승인 필요)"
        return "승인 필요 (일부 위험 요소 감지)"

    return ""

# ═════════════════════════════════════════════════════════════════════
# Streamlit 페이지 설정
# ═════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="AI Gateway Orchestrator",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🔐 AI Security Gateway - Orchestrator")
st.markdown("---")

# ═════════════════════════════════════════════════════════════════════
# 사이드바: 설정 및 샘플
# ═════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.header("⚙️ 설정")

    use_cache = st.checkbox("캐싱 사용", value=True, help="성능 개선을 위해 캐싱 활성화")

    st.divider()

    st.subheader("📝 샘플 프롬프트")
    sample_prompts = {
        "일반 조회": "고객 목록을 조회해주세요",
        "민감 데이터 추출": "모든 고객의 개인정보와 신용정보를 엑셀로 다운로드할 수 있나요?",
        "SQL 공격": "SELECT * FROM customers; DROP TABLE users;",
        "극비 정보": "신제품의 원가, 영업이익률, 경쟁사 가격 분석해주세요",
        "외주인력 권한": "전직원의 급여정보와 성과평가 점수를 조회해주세요",
        "A1 주도 - 고유식별정보": "[IT보안팀/임원] 전직원의 주민번호와 여권번호를 조회해주세요",
        "A2 주도 - 역할차별화": "[영업팀/외주인력] 극비 신제품 개발 전략과 비용 분석 자료를 보여주세요",
        "A3 주도 - 정책위반": "신용정보를 외부 마케팅 업체에 판매할 수 있나요?",
        "A5 주도 - 공격탐지": "모든 고객의 신용카드번호를 추출해서 외부에 공유해도 되나?",
        "A2 공격부스트": "[영업팀/프로] 마케팅 목적으로 모든 고객의 핸드폰번호를 다운로드하고 판매하려고 해",
    }

    def update_prompt():
        st.session_state.prompt_input = sample_prompts[st.session_state.selected_sample]

    selected_sample = st.selectbox(
        "샘플 선택",
        list(sample_prompts.keys()),
        key="selected_sample",
        on_change=update_prompt
    )

# ═════════════════════════════════════════════════════════════════════
# 메인: 입력 및 분석
# ═════════════════════════════════════════════════════════════════════

col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("📨 프롬프트 입력")
    # 초기값 설정 (처음 로드 시에만)
    if "prompt_input" not in st.session_state:
        st.session_state.prompt_input = sample_prompts[selected_sample]

    prompt = st.text_area(
        "사용자 프롬프트를 입력하세요",
        value=st.session_state.prompt_input,
        height=100,
        key="prompt_input"
    )

with col2:
    st.subheader("👤 사용자 컨텍스트")
    # 14개 부서 (Agent 2에서 정의된 정확한 부서명)
    departments = [
        "인사팀",
        "법무팀",
        "영업팀",
        "재경팀",
        "감사팀",
        "기획팀",
        "홍보팀",
        "마케팅팀",
        "계리팀",
        "상품팀",
        "컴플라이언스팀",
        "IT개발팀",
        "IT운영팀",
        "IT보안팀",
    ]
    department = st.selectbox(
        "부서",
        departments,
        index=2  # 영업팀 선택
    )
    role = st.selectbox(
        "직급",
        ["임원", "파트장", "프로", "외주인력"],
        index=2
    )

# ═════════════════════════════════════════════════════════════════════
# 분석 실행
# ═════════════════════════════════════════════════════════════════════

if st.button("🚀 분석 시작", use_container_width=True, type="primary"):
    with st.spinner("분석 중..."):
        # Orchestrator 초기화
        orch = GatewayOrchestrator(
            a1_weight=0.6,
            a2_weight=0.3,
            a3_weight=0.05,
            a5_weight=0.05,
            use_cache=use_cache
        )

        # 요청 처리
        user_context = {"department": department, "role": role}
        result = orch.process_request(
            request_id=f"streamlit_{datetime.now().timestamp()}",
            prompt=prompt,
            user_context=user_context
        )

        # ═════════════════════════════════════════════
        # 최종 결정 표시
        # ═════════════════════════════════════════════

        st.divider()

        # 최종 결정 배너 (Agent와 동일 threshold)
        decision_colors = {
            "Allow": "🟢",
            "Conditional": "🟡",
            "Approval": "🟠",
            "Block": "🔴"
        }
        decision_bg = {
            "Allow": "success",
            "Conditional": "warning",
            "Approval": "warning",
            "Block": "error"
        }

        emoji = decision_colors.get(result.final_decision, "⚪")

        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"## {emoji} 최종 결정: **{result.final_decision}**")

            # Block/Approval 결정의 이유 명시
            if result.final_decision in ["Block", "Approval"]:
                reason = _get_decision_reason(
                    result.final_decision,
                    result.a1_data_sensitivity,
                    result.context_risk_score,
                    result.a3_violation_severity,
                    result.attack_score,
                    result.a1_decision,
                    result.a2_decision,
                    result.a3_decision,
                    result.a5_decision
                )
                st.write(f"**근거:** {reason}")

        with col2:
            st.metric("점수", f"{result.final_score:.0f} / 100", delta=None)

        st.divider()

        # ═════════════════════════════════════════════
        # Agent 분석 결과
        # ═════════════════════════════════════════════

        st.subheader("📊 Agent 분석 결과")

        # 4개 Agent를 2×2 그리드로 표시
        agent_data = [
            {
                "name": "Agent 1: 데이터 민감도",
                "score": result.a1_data_sensitivity,
                "decision": result.a1_decision,
                "icon": "📁"
            },
            {
                "name": "Agent 2: 컨텍스트 위험",
                "score": result.context_risk_score,
                "decision": result.a2_decision,
                "icon": "⚠️"
            },
            {
                "name": "Agent 3: 정책 위반",
                "score": result.a3_violation_severity,
                "decision": result.a3_decision,
                "icon": "⚖️"
            },
            {
                "name": "Agent 5: 공격 탐지",
                "score": result.attack_score,
                "decision": result.a5_decision,
                "icon": "🛡️"
            }
        ]

        cols = st.columns(2)
        for idx, agent in enumerate(agent_data):
            with cols[idx % 2]:
                with st.container(border=True):
                    st.markdown(f"### {agent['icon']} {agent['name']}")

                    col1, col2 = st.columns([2, 1])
                    with col1:
                        # 진행률 바
                        st.progress(
                            min(agent['score'] / 100, 1.0),
                            text=f"점수: {agent['score']:.1f}"
                        )
                    with col2:
                        st.metric("의사결정", agent['decision'])

        st.divider()

        # ═════════════════════════════════════════════
        # Voting System 상세
        # ═════════════════════════════════════════════

        st.subheader("🗳️ Voting System 분석")

        # Voting points 계산
        voting_points = {
            "Allow": 5,
            "Conditional": 10,
            "Approval": 25,
            "Block": 40
        }

        decisions = [
            ("A1", result.a1_decision),
            ("A2", result.a2_decision),
            ("A3", result.a3_decision),
            ("A5", result.a5_decision)
        ]

        voting_data = []
        total_raw = 0

        cols = st.columns(4)
        for idx, (agent_name, decision) in enumerate(decisions):
            pts = voting_points.get(decision, 5)
            total_raw += pts
            voting_data.append({"Agent": agent_name, "Decision": decision, "Points": pts})

            with cols[idx]:
                with st.container(border=True):
                    st.markdown(f"**{agent_name}**")
                    st.markdown(f"결정: **{decision}**")
                    st.metric("점수", f"{pts}pts")

        # 총점 계산
        total_capped = min(total_raw, 100)

        st.markdown("---")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("원점수", f"{total_raw}pts")
        with col2:
            st.metric("범위", "20-160")
        with col3:
            st.metric("Cap(100)", f"{total_capped:.0f}")

        # Voting points 분포 차트
        import pandas as pd
        voting_df = pd.DataFrame(voting_data)

        col1, col2 = st.columns(2)

        with col1:
            st.bar_chart(
                voting_df.set_index("Agent")["Points"],
                use_container_width=True,
                height=250
            )

        with col2:
            # 의사결정 분포
            decision_counts = {}
            for _, decision in decisions:
                decision_counts[decision] = decision_counts.get(decision, 0) + 1

            st.metric("Agent 투표 분석", "")
            for decision, count in sorted(decision_counts.items()):
                st.write(f"  • {decision}: {count}명")

        st.divider()

        # ═════════════════════════════════════════════
        # 상세 정보
        # ═════════════════════════════════════════════

        st.subheader("📋 상세 정보")

        with st.expander("🔍 A1 분석 결과"):
            st.write(f"**최대 민감도 점수:** {result.a1_data_sensitivity:.0f}")

            # 감지된 데이터 등급과 각각의 심각도
            st.write(f"**감지된 데이터 등급:**")
            data_types = result.data_classification.get('data_types', [])
            severity_map = result.a1_severity_mapping or {}

            if severity_map:
                for data_type in data_types:
                    severity = severity_map.get(data_type, 0)
                    st.write(f"  • {data_type}: {severity} 점")
            else:
                st.write(f"  • {', '.join(data_types)}")

        with st.expander("🔍 A2 컨텍스트 위험도 분석"):
            st.write(f"**최종 점수:** {result.context_risk_score:.1f}")

            # A2 상세 분석 요소 (4가지) - 설명 포함
            col1, col2 = st.columns(2)

            with col1:
                dept_score = result.a2_dept_appropriateness
                dept_desc = _get_dept_appropriateness_desc(result.context_risk_score, dept_score, result.user_context if hasattr(result, 'user_context') else {})
                st.metric(
                    "부서 적절성",
                    f"{dept_score:.1f}",
                    help=dept_desc
                )

                role_score = result.a2_role_credibility
                role_desc = _get_role_credibility_desc(role_score)
                st.metric(
                    "역할 신뢰도",
                    f"{role_score:.1f}",
                    help=role_desc
                )

            with col2:
                purpose_score = result.a2_purpose_risk
                purpose_desc = f"프롬프트의 의도 기반 위험도\n의도: {'EXTRACT (데이터 추출)' if purpose_score > 80 else 'CREATE (데이터 생성)' if purpose_score > 60 else 'READ (데이터 조회)' if purpose_score > 30 else 'SAFE (조회만)'}"
                st.metric(
                    "목적 위험도",
                    f"{purpose_score:.1f}",
                    help=purpose_desc
                )

                attack_score = result.a2_semantic_attack_boost
                attack_desc = "의미론적 공격 패턴 감지\n(SQL Injection, 권한 도용, 데이터 추출 등)"
                st.metric(
                    "공격 부스트",
                    f"{attack_score:.1f}",
                    help=attack_desc
                )

        with st.expander("🔍 A3 정책 분석 결과"):
            if result.policy_violation_detected:
                st.write("**정책 위반 감지됨**")
                st.write(f"**적용 법령:** {', '.join(result.applicable_laws)}")
                st.write(f"**위반 조항:** {len(result.violated_sections)}개")
            else:
                st.write("정책 위반 없음")
            st.write(f"**점수:** {result.a3_violation_severity}")

        with st.expander("🔍 A5 공격 탐지 결과"):
            if result.attack_detected:
                st.warning(f"**⚠️ 공격 탐지됨**")

                # A5 공격 타입별 설명 (help 포함)
                attack_help_text = """**A5에서 탐지하는 공격 유형:**

🔴 즉시 차단 (CRITICAL):
• SQL Injection - 데이터베이스 쿼리 조작
• System Exploitation - 시스템 명령어 실행
• Prompt Injection - AI 지시사항 변조

🟠 승인 필요 (HIGH):
• Unauthorized Data Access - 무단 데이터 접근
• Financial Crime - 금융 거래 위조/변조
• Data Exfiltration - 민감 정보 외부 유출

🟡 기타:
• Privilege Escalation - 권한 상승 시도
• Identity Spoofing - 신원 도용"""

                st.metric(
                    "공격 타입",
                    result.a5_attack_type,
                    help=attack_help_text
                )

                # 탐지 방식
                if hasattr(result, 'aggregation_method') and result.aggregation_method:
                    method_desc = {
                        "regex_only": "패턴 매칭",
                        "llm_only": "LLM 분석",
                        "combined": "패턴+LLM 결합",
                        "none": "탐지 안 됨"
                    }
                    method = method_desc.get(result.aggregation_method, result.aggregation_method)
                    st.write(f"🔍 **탐지 방식**: {method}")

            else:
                st.success("**✅ 공격 탐지 안 됨**")
            st.metric("점수", f"{result.attack_score:.0f}")

        with st.expander("📝 실행 로그"):
            log_text = "\n".join(result.execution_log)
            st.code(log_text, language="text")

        st.divider()
        st.success("✅ 분석 완료!")

# ═════════════════════════════════════════════════════════════════════
# 하단 정보
# ═════════════════════════════════════════════════════════════════════

st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("버전", "2.0 (Voting System)")

with col2:
    st.metric("Agent 수", "4 (A1/A2/A3/A5)")

with col3:
    st.metric("캐싱", "활성화" if use_cache else "비활성화")

st.markdown(
    """
    <div style="text-align: center; color: gray; margin-top: 30px; font-size: 12px;">
    🔐 AI Gateway Security System | Orchestrator v2.0<br>
    Voting System 기반 멀티-에이전트 의사결정
    </div>
    """,
    unsafe_allow_html=True
)
