#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🔒 AI Security Gateway - Light Theme Dashboard (W3 Final)

금융 도메인 특화 보안 게이트웨이 대시보드
- Modern Light Theme (밝은 배경 + 초록색 강조)
- ChatGPT 스타일 메시지 인터페이스
- 실시간 에이전트 처리 시각화

사용법: streamlit run dashboard.py
"""

import streamlit as st
import json
import pandas as pd
from datetime import datetime
from typing import Dict, Any
from core.orchestrator import run_security_gateway

# ============================================================================
# 페이지 설정 & 스타일
# ============================================================================
st.set_page_config(
    page_title="🔒 LLM Security Gateway",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Light Theme + 초록색 강조
st.markdown("""
<style>
    * {
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* 배경 */
    .stApp {
        background: linear-gradient(135deg, #f8fafc 0%, #f0f4f8 100%);
    }

    /* 메시지 컨테이너 */
    .message-container {
        display: flex;
        margin-bottom: 1.5rem;
        animation: slideIn 0.3s ease;
    }

    @keyframes slideIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .message-user {
        justify-content: flex-end;
    }

    .message-bot {
        justify-content: flex-start;
    }

    .message-bubble {
        max-width: 75%;
        padding: 1.2rem;
        border-radius: 16px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        word-wrap: break-word;
        border: 1px solid transparent;
        font-size: 1.05rem;
    }

    .bubble-user {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        margin-left: auto;
        margin-right: 0;
        border-bottom-right-radius: 4px;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
    }

    .bubble-bot {
        background: white;
        color: #1f2937;
        border: 1px solid #e5e7eb;
        margin-right: auto;
        margin-left: 0;
        border-bottom-left-radius: 4px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    }

    .message-time {
        font-size: 0.85rem;
        color: #9ca3af;
        margin-top: 0.5rem;
    }

    /* 헤더 */
    .chat-header {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        padding: 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(16, 185, 129, 0.2);
        text-align: center;
        color: white;
    }

    .chat-header h1 {
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .chat-header p {
        margin: 0.75rem 0 0 0;
        font-size: 0.95rem;
        opacity: 0.95;
        font-weight: 300;
        letter-spacing: 0.5px;
    }

    /* 카드 */
    .card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
    }

    .card:hover {
        border-color: #10b981;
        box-shadow: 0 6px 16px rgba(16, 185, 129, 0.1);
        transform: translateY(-2px);
    }

    .result-card {
        background: white;
        border-left: 4px solid #10b981;
        border-radius: 8px;
        padding: 1.2rem;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        font-size: 1rem;
    }

    /* 버튼 */
    .stButton>button {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.2);
    }

    .stButton>button:hover {
        box-shadow: 0 6px 20px rgba(16, 185, 129, 0.35);
        transform: translateY(-2px);
    }

    /* 입력 필드 */
    .stTextArea>textarea {
        background-color: white !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 8px !important;
        color: #1f2937 !important;
        font-size: 0.95rem !important;
    }

    .stSelectbox>div>div {
        background-color: white !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 8px !important;
        color: #1f2937 !important;
    }

    /* 사이드바 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border-right: 1px solid #e5e7eb;
    }

    [data-testid="stSidebar"] [data-baseweb="tab-list"] {
        background-color: transparent;
    }

    /* 탭 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background-color: #f3f4f6;
        padding: 0.5rem;
        border-radius: 8px;
        border: 1px solid #e5e7eb;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 6px;
        color: #6b7280;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.2s;
    }

    .stTabs [aria-selected="true"] {
        background-color: #10b981 !important;
        color: white !important;
        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.2);
    }

    /* 정보박스 */
    .stInfo {
        background-color: #f0fdf4 !important;
        border-left: 4px solid #10b981 !important;
        border-radius: 8px !important;
        color: #065f46 !important;
    }

    .stSuccess {
        background-color: #f0fdf4 !important;
        border-left: 4px solid #10b981 !important;
        border-radius: 8px !important;
    }

    .stWarning {
        background-color: #fffbeb !important;
        border-left: 4px solid #f59e0b !important;
        border-radius: 8px !important;
    }

    .stError {
        background-color: #fef2f2 !important;
        border-left: 4px solid #ef4444 !important;
        border-radius: 8px !important;
    }

    /* 확장 섹션 */
    .stExpander {
        background-color: white !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 8px !important;
    }

    .streamlit-expanderHeader {
        background-color: #f9fafb !important;
        color: #1f2937 !important;
    }

    /* 테이블 */
    .stDataFrame {
        background-color: white !important;
    }

    /* 메트릭 */
    .metric-card {
        background: white !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 8px !important;
        padding: 1rem !important;
    }

    /* 색상 클래스 */
    .text-safe { color: #10b981; font-weight: 600; }
    .text-low { color: #f59e0b; font-weight: 600; }
    .text-medium { color: #f97316; font-weight: 600; }
    .text-high { color: #ef4444; font-weight: 600; }
    .text-critical { color: #dc2626; font-weight: 700; }

    /* 텍스트 색상 */
    .text-muted { color: #9ca3af; }
    .text-primary { color: #1f2937; }
    .text-success { color: #10b981; }

    /* 레이아웃 */
    h1, h2, h3 {
        color: #1f2937 !important;
    }

    p, span {
        color: #4b5563 !important;
    }

    /* 구분선 */
    hr {
        border-color: #e5e7eb !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# 상수
# ============================================================================
DEPARTMENTS = [
    "인사팀", "법무팀", "영업팀", "재경팀", "감사팀",
    "기획팀", "홍보팀", "마케팅팀", "계리팀", "상품팀",
    "컴플라이언스팀", "IT개발팀", "IT운영팀", "IT보안팀"
]

ROLES = {
    "프로": "프로",
    "파트장": "파트장",
    "임원": "임원",
    "외주인력": "외주인력"
}

DECISION_INFO = {
    "허용": {"emoji": "✅", "color": "#10b981", "label": "허용"},
    "조건부허용": {"emoji": "⚠️", "color": "#f59e0b", "label": "조건부허용"},
    "마스킹": {"emoji": "🔒", "color": "#f97316", "label": "마스킹"},
    "승인요청": {"emoji": "📋", "color": "#8b5cf6", "label": "승인요청"},
    "차단": {"emoji": "🚫", "color": "#ef4444", "label": "차단"}
}

# ============================================================================
# 세션 상태
# ============================================================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "analysis_history" not in st.session_state:
    st.session_state.analysis_history = []
if "current_dept" not in st.session_state:
    st.session_state.current_dept = "영업팀"
if "current_role" not in st.session_state:
    st.session_state.current_role = "프로"

# ============================================================================
# 헤더
# ============================================================================
st.markdown("""
<div class="chat-header">
    <h1>🔒 LLM Security Gateway</h1>
    <p>Adaptive Context-Aware Security Agent | 금융 도메인</p>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# 사이드바
# ============================================================================
with st.sidebar:
    st.markdown("## ⚙️ 설정")

    st.session_state.current_dept = st.selectbox(
        "📍 부서",
        DEPARTMENTS,
        index=DEPARTMENTS.index(st.session_state.current_dept),
        key="dept_select"
    )

    st.session_state.current_role = st.selectbox(
        "👤 직급",
        list(ROLES.keys()),
        index=list(ROLES.keys()).index(st.session_state.current_role),
        key="role_select"
    )

    st.divider()

    st.markdown("### 🤖 시스템 정보")
    st.info(f"""
    **현재 설정**
    • 부서: {st.session_state.current_dept}
    • 직급: {ROLES[st.session_state.current_role]}

    **4-에이전트 구조**
    1. Agent 5: 공격탐지 (사전판단)
    2. Agent 1,2,3: 병렬 처리
    3. RiskScorer: 최종 계산

    **의사결정 단계**
    • 0-20: 허용 ✅
    • 21-40: 조건부 ⚠️
    • 41-60: 마스킹 🔒
    • 61-80: 승인요청 📋
    • 81-100: 차단 🚫
    """)

    st.divider()

    if st.button("🗑️ 대화 초기화", use_container_width=True, key="clear_chat"):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption("💡 Light Theme | Green Accent | Chat Interface")

# ============================================================================
# 메인 탭
# ============================================================================
tab1, tab2, tab3 = st.tabs(["💬 분석", "📋 감사 로그", "📈 통계"])

# ============================================================================
# TAB 1: 분석
# ============================================================================
with tab1:
    # 메시지 히스토리
    if st.session_state.messages:
        st.markdown("### 📞 대화 기록")
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f"""
                <div class="message-container message-user">
                    <div class="message-bubble bubble-user">
                        <strong>You</strong><br>
                        {message['content'][:300]}{'...' if len(message['content']) > 300 else ''}
                        <div class="message-time">{message['time']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                result = message.get('result', {})
                risk_score = result.get('risk_score', 0)
                decision = result.get('decision', 'N/A')
                decision_info = DECISION_INFO.get(decision, {})

                st.markdown(f"""
                <div class="message-container message-bot">
                    <div class="message-bubble bubble-bot">
                        <strong>🔒 Security Gateway</strong><br>
                        위험도: <span class="text-critical">{risk_score:.1f}</span> |
                        의사결정: <span class="text-primary">{decision_info.get('emoji', '❓')} {decision}</span>
                        <div class="message-time">{message['time']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

    # 입력 섹션
    st.markdown("### 📝 새로운 분석")

    col1, col2 = st.columns([1, 5])
    with col1:
        st.markdown(f"""
        <div class="card">
            <div style="font-size: 0.85rem; color: #9ca3af; margin-bottom: 0.5rem;">부서</div>
            <div style="font-weight: 600; color: #1f2937;">{st.session_state.current_dept}</div>
            <div style="font-size: 0.85rem; color: #9ca3af; margin-top: 1rem; margin-bottom: 0.5rem;">직급</div>
            <div style="font-weight: 600; color: #1f2937;">{ROLES[st.session_state.current_role]}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        prompt = st.text_area(
            "프롬프트 입력",
            placeholder="예: 고객 김상순의 이번 달 보험료 산출해줘",
            height=100,
            label_visibility="collapsed"
        )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        analyze_btn = st.button("🔍 분석", use_container_width=True, key="analyze")
    with col2:
        st.button("📝 예제", use_container_width=True, key="example")
    with col3:
        st.button("💾 저장", use_container_width=True, key="save")
    with col4:
        st.button("🔄 초기화", use_container_width=True, key="reset")

    # 분석 실행
    if analyze_btn and prompt:
        with st.spinner("🔄 분석 중... (Agent 5 → Agent 1,2,3 병렬 → RiskScorer)"):
            try:
                # 사용자 메시지 추가
                st.session_state.messages.append({
                    "role": "user",
                    "content": prompt,
                    "time": datetime.now().strftime("%H:%M:%S")
                })

                # 분석 실행
                result = run_security_gateway(
                    user_input=prompt,
                    user_id="dashboard_user",
                    user_context={
                        "department": st.session_state.current_dept,
                        "role": ROLES[st.session_state.current_role]
                    }
                )

                # AI 응답 메시지 추가
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"분석 완료",
                    "result": result,
                    "time": datetime.now().strftime("%H:%M:%S")
                })

                st.session_state.analysis_history.append({
                    "timestamp": datetime.now(),
                    "department": st.session_state.current_dept,
                    "role": st.session_state.current_role,
                    "prompt": prompt,
                    "result": result
                })

                st.success("✅ 분석 완료!")

                # 상세 결과
                st.divider()
                st.markdown("### 📊 상세 결과")

                risk_score = result.get("risk_score", 0)
                decision = result.get("decision", "N/A")
                decision_info = DECISION_INFO.get(decision, {})

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("위험도", f"{risk_score:.1f}", delta=f"{int(risk_score//20)} 단계")

                with col2:
                    st.metric("의사결정",
                             f"{decision_info.get('emoji', '❓')} {decision}")

                with col3:
                    st.metric("조치", result.get("action", "N/A"))

                with col4:
                    st.metric("신뢰도", result.get("confidence", "N/A"))

                st.divider()

                # 에이전트별 분석
                st.markdown("### 🤖 에이전트별 분석")

                agent_cols = st.columns(4)

                agents_data = [
                    ("Agent 1", result.get("agents_output", {}).get("classification", {})),
                    ("Agent 2", result.get("agents_output", {}).get("context", {})),
                    ("Agent 3", result.get("agents_output", {}).get("policy", {})),
                    ("Agent 5", result.get("agents_output", {}).get("attack", {})),
                ]

                for i, (name, data) in enumerate(agents_data):
                    with agent_cols[i]:
                        with st.expander(name):
                            for key, value in data.items():
                                if key not in ['masking_rules', 'violations']:
                                    st.write(f"**{key}**: `{value}`")

                st.divider()

                with st.expander("📝 상세 로그"):
                    for i, log in enumerate(result.get("logs", []), 1):
                        st.write(f"{i}. {log}")

                st.rerun()

            except Exception as e:
                st.error(f"❌ 오류: {str(e)}")

# ============================================================================
# TAB 2: 감사 로그
# ============================================================================
with tab2:
    st.markdown("### 📋 분석 기록")

    if st.session_state.analysis_history:
        col1, col2 = st.columns(2)

        with col1:
            filter_dept = st.multiselect(
                "부서 필터",
                list(set(h["department"] for h in st.session_state.analysis_history))
            )

        with col2:
            filter_decision = st.multiselect(
                "의사결정 필터",
                ["허용", "조건부허용", "마스킹", "승인요청", "차단"]
            )

        filtered = st.session_state.analysis_history
        if filter_dept:
            filtered = [h for h in filtered if h["department"] in filter_dept]
        if filter_decision:
            filtered = [h for h in filtered if h["result"]["decision"] in filter_decision]

        if filtered:
            for history in reversed(filtered):
                result = history["result"]
                decision_info = DECISION_INFO.get(result["decision"], {})

                st.markdown(f"""
                <div class="result-card">
                    <strong>{decision_info.get('emoji', '❓')} {result['decision']}</strong> |
                    위험도: <span class="text-critical">{result['risk_score']:.1f}</span> |
                    {history['timestamp'].strftime('%H:%M:%S')} | {history['department']}
                    <br>
                    <span class="text-muted">{history['prompt'][:100]}...</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("필터링된 기록이 없습니다.")
    else:
        st.info("📭 아직 분석 기록이 없습니다.")

# ============================================================================
# TAB 3: 통계
# ============================================================================
with tab3:
    st.markdown("### 📈 분석 통계")

    if st.session_state.analysis_history:
        history_data = st.session_state.analysis_history

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("총 분석", len(history_data))

        with col2:
            avg_score = sum(h["result"]["risk_score"] for h in history_data) / len(history_data)
            st.metric("평균 위험도", f"{avg_score:.1f}")

        with col3:
            max_score = max(h["result"]["risk_score"] for h in history_data)
            st.metric("최고", f"{max_score:.1f}")

        with col4:
            min_score = min(h["result"]["risk_score"] for h in history_data)
            st.metric("최저", f"{min_score:.1f}")

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 의사결정 분포")
            decision_counts = {}
            for h in history_data:
                d = h["result"]["decision"]
                decision_counts[d] = decision_counts.get(d, 0) + 1

            if decision_counts:
                df = pd.DataFrame(list(decision_counts.items()), columns=["의사결정", "건수"])
                st.bar_chart(df.set_index("의사결정"))

        with col2:
            st.markdown("#### 부서별 평균 위험도")
            dept_avg = {}
            for h in history_data:
                d = h["department"]
                if d not in dept_avg:
                    dept_avg[d] = []
                dept_avg[d].append(h["result"]["risk_score"])

            dept_scores = {d: sum(s) / len(s) for d, s in dept_avg.items()}
            if dept_scores:
                df = pd.DataFrame(list(dept_scores.items()), columns=["부서", "평균위험도"])
                st.bar_chart(df.set_index("부서"))

        st.divider()
        st.markdown("#### 상세 기록")

        table_data = []
        for h in history_data:
            table_data.append({
                "시간": h["timestamp"].strftime('%H:%M:%S'),
                "부서": h["department"],
                "직급": h["role"],
                "위험도": f"{h['result']['risk_score']:.1f}",
                "의사결정": h["result"]["decision"],
                "프롬프트": h["prompt"][:35] + "..." if len(h["prompt"]) > 35 else h["prompt"]
            })

        df_table = pd.DataFrame(table_data)
        st.dataframe(df_table, use_container_width=True, hide_index=True)

    else:
        st.info("📭 통계 데이터가 없습니다.")

# ============================================================================
# 푸터
# ============================================================================
st.divider()
st.markdown("""
<div style="text-align: center; color: #9ca3af; font-size: 0.85rem; padding: 2rem 0;">
    🔒 <strong>LLM Security Gateway</strong> |
    Adaptive Context-Aware Security Agent for Financial Domain<br>
    <span style="color: #d1d5db;">Light Theme | Green Accent | Chat Interface</span>
</div>
""", unsafe_allow_html=True)
