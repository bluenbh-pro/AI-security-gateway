#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI Security Gateway - Professional Streamlit Demo
학회 발표용 고품질 대시보드 (AAAI/FinNLP 발표)

기능:
- 임직원이 프롬프트 + 파일 입력
- Orchestrator가 5가지 Agent로 분석
- 실시간 위험도 점수 및 의사결정 출력
- 시각화: 게이지, 막대 그래프, 상세 로그

사용법:
    streamlit run streamlit_demo_pro.py
"""

import streamlit as st
import json
from datetime import datetime
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.orchestrator import GatewayOrchestrator

# ===== PAGE CONFIG =====
st.set_page_config(
    page_title="AI Security Gateway",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ===== CUSTOM CSS =====
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }

    .header-title {
        font-size: 2.5em;
        font-weight: 700;
        color: #1f3a93;
        margin-bottom: 0.3em;
    }

    .header-subtitle {
        font-size: 1.1em;
        color: #666;
        margin-bottom: 2em;
    }

    .section-title {
        font-size: 1.2em;
        font-weight: 600;
        color: #1f3a93;
        margin-bottom: 1em;
        padding-bottom: 0.5em;
        border-bottom: 2px solid #1f3a93;
    }

    .decision-allow {
        background-color: #d4edda;
        color: #155724;
        border: 2px solid #28a745;
        padding: 1.5em;
        border-radius: 8px;
        text-align: center;
        font-weight: 600;
        font-size: 1.3em;
        margin-bottom: 1.5em;
    }

    .decision-conditional {
        background-color: #fff3cd;
        color: #856404;
        border: 2px solid #ffc107;
        padding: 1.5em;
        border-radius: 8px;
        text-align: center;
        font-weight: 600;
        font-size: 1.3em;
        margin-bottom: 1.5em;
    }

    .decision-approval {
        background-color: #e2e3e5;
        color: #383d41;
        border: 2px solid #6c757d;
        padding: 1.5em;
        border-radius: 8px;
        text-align: center;
        font-weight: 600;
        font-size: 1.3em;
        margin-bottom: 1.5em;
    }

    .decision-block {
        background-color: #f8d7da;
        color: #721c24;
        border: 2px solid #dc3545;
        padding: 1.5em;
        border-radius: 8px;
        text-align: center;
        font-weight: 600;
        font-size: 1.3em;
        margin-bottom: 1.5em;
    }

    .score-badge {
        display: inline-block;
        padding: 0.5em 1em;
        border-radius: 6px;
        font-weight: 600;
        font-size: 1.1em;
        margin: 0.5em 0.5em 0.5em 0;
    }

    .score-high { background-color: #f8d7da; color: #721c24; }
    .score-medium { background-color: #fff3cd; color: #856404; }
    .score-low { background-color: #d4edda; color: #155724; }
</style>
""", unsafe_allow_html=True)

# ===== SESSION STATE =====
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = GatewayOrchestrator()

if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None

# ===== HELPER FUNCTIONS =====
def get_decision_class(decision: str) -> str:
    if decision == "Allow":
        return "decision-allow"
    elif decision == "Conditional Allow":
        return "decision-conditional"
    elif decision == "Approval Required":
        return "decision-approval"
    else:
        return "decision-block"

def get_decision_emoji(decision: str) -> str:
    emojis = {
        "Allow": "✅",
        "Conditional Allow": "⚠️",
        "Approval Required": "⏳",
        "Block": "🚫"
    }
    return emojis.get(decision, "❓")

def get_score_class(score: float) -> str:
    if score >= 70:
        return "score-high"
    elif score >= 40:
        return "score-medium"
    else:
        return "score-low"

# ===== MAIN UI =====
# 헤더
st.markdown('<div class="header-title">🔒 AI Security Gateway</div>', unsafe_allow_html=True)
st.markdown('<div class="header-subtitle">금융권 LLM 보안 게이트웨이: 임직원 요청 실시간 분석</div>', unsafe_allow_html=True)

# 메인 레이아웃
col_input, col_result = st.columns([0.4, 0.6], gap="large")

# ===== LEFT PANEL =====
with col_input:
    st.markdown('<div class="section-title">📝 요청 분석</div>', unsafe_allow_html=True)

    # 사용자 정보
    st.markdown("**👤 사용자 정보**")
    col_dept, col_role = st.columns(2)
    with col_dept:
        departments = ["인사팀", "법무팀", "영업팀", "재경팀", "감사팀", "기획팀", "홍보팀",
                      "마케팅팀", "계리팀", "상품팀", "컴플라이언스팀", "IT개발팀", "IT운영팀", "IT보안팀"]
        department = st.selectbox("부서", departments, label_visibility="collapsed")
    with col_role:
        role = st.selectbox("직급", ["임원", "파트장", "프로", "외주인력"], label_visibility="collapsed")

    user_id = st.text_input("사용자 ID", value="user_001", label_visibility="collapsed")

    st.divider()

    # 프롬프트
    st.markdown("**💬 프롬프트**")
    prompt = st.text_area("프롬프트", height=150, placeholder="분석할 프롬프트를 입력하세요", label_visibility="collapsed")

    st.divider()

    # 파일 업로드
    st.markdown("**📎 파일 (선택사항)**")
    uploaded_file = st.file_uploader("파일", type=["txt", "csv", "json", "xlsx", "pdf"], label_visibility="collapsed")

    file_paths = []
    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
            tmp.write(uploaded_file.getbuffer())
            file_paths = [tmp.name]
        st.success(f"✅ {uploaded_file.name} 업로드됨")

    st.divider()

    # 분석 버튼
    if st.button("🔍 분석 시작", use_container_width=True, type="primary"):
        if not prompt.strip():
            st.error("⚠️ 프롬프트를 입력하세요")
        else:
            with st.spinner("분석 중..."):
                try:
                    result = st.session_state.orchestrator.process_request(
                        request_id=f"req-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        prompt=prompt,
                        file_paths=file_paths if file_paths else None,
                        user_context={"user_id": user_id, "department": department, "role": role}
                    )
                    st.session_state.analysis_result = result
                except Exception as e:
                    st.error(f"❌ 오류: {str(e)}")

# ===== RIGHT PANEL =====
with col_result:
    st.markdown('<div class="section-title">📊 분석 결과</div>', unsafe_allow_html=True)

    if st.session_state.analysis_result is None:
        st.info("💡 좌측에서 프롬프트를 입력하고 분석을 시작하세요")
    else:
        result = st.session_state.analysis_result

        # 의사결정
        decision_emoji = get_decision_emoji(result.final_decision)
        decision_text = {"Allow": "허용", "Conditional Allow": "조건부허용", "Approval Required": "승인필요", "Block": "차단"}.get(result.final_decision, "미정")
        st.markdown(f'<div class="{get_decision_class(result.final_decision)}">{decision_emoji} {decision_text}</div>', unsafe_allow_html=True)

        # 위험도
        st.markdown("**⚠️ 위험도 점수**")
        col_gauge, col_num = st.columns([0.7, 0.3])
        with col_gauge:
            st.progress(result.final_score / 100)
        with col_num:
            st.metric("", f"{result.final_score:.1f}/100")

        # Agent 점수
        st.markdown("**🤖 Agent별 점수**")
        cols = st.columns(3, gap="small")
        scores = [
            ("📊 Data (40%)", result.data_classification.get("risk_score", 0)),
            ("🛡️ Policy (30%)", result.policy_risk_score),
            ("👤 Context (30%)", result.context_risk_score)
        ]
        for idx, (label, score) in enumerate(scores):
            with cols[idx]:
                st.markdown(f"**{label}**")
                st.markdown(f'<span class="score-badge {get_score_class(score)}">{score:.0f}</span>', unsafe_allow_html=True)

        # 상세 분석
        st.markdown("**📋 상세**")
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("**데이터 타입**")
            if result.data_classification.get("data_types"):
                for dtype in result.data_classification.get("data_types", []):
                    st.write(f"• {dtype}")
            else:
                st.write("• 일반 데이터")

        with col_b:
            st.write("**민감도**")
            st.write(f"• {result.data_classification.get('sensitivity_level', '무난')}")

        st.divider()

        # Agent별 상세 분석
        st.markdown("**🔍 Agent별 분석 결과**")

        # Agent 1: 데이터 민감도
        agent1_score = result.data_classification.get("risk_score", 0)
        agent1_sensitivity = result.data_classification.get("sensitivity_level", "무난")
        agent1_datatypes = result.data_classification.get("data_types", ["general"])

        col_a1, col_a2, col_a3 = st.columns(3)
        with col_a1:
            st.metric("📊 Agent 1 (40%)", f"{agent1_score:.0f}", "데이터 민감도")
            st.caption(f"레벨: {agent1_sensitivity}")
            if agent1_datatypes != ["general"]:
                st.caption(f"데이터: {', '.join(agent1_datatypes)}")

        # Agent 2: 컨텍스트 위험도
        with col_a2:
            st.metric("👤 Agent 2 (30%)", f"{result.context_risk_score:.0f}", "컨텍스트 위험도")
            st.caption(f"역할: {result.execution_log[2] if len(result.execution_log) > 2 else '분석 중'}")

        # Agent 3: 정책 위반
        with col_a3:
            st.metric("🛡️ Agent 3 (30%)", f"{result.policy_risk_score:.0f}", "정책 위반 위험")
            if result.policy_violation_detected:
                st.caption("⚠️ 정책 위반 감지")
            else:
                st.caption("✅ 정책 준수")

        st.divider()

        # 설명 및 추천
        st.markdown("**💡 상세 분석 의견**")

        analysis_text = []

        # Agent 1 분석
        analysis_text.append(f"🔹 **데이터 민감도 (Agent 1 - {agent1_score:.0f}/100)**")
        if agent1_score <= 15:
            analysis_text.append("   - 일반 데이터만 포함, 민감도 낮음")
        elif agent1_score <= 50:
            analysis_text.append(f"   - {agent1_sensitivity} 수준의 데이터 감지")
        else:
            analysis_text.append(f"   - {agent1_sensitivity} 데이터 포함 ({', '.join([d for d in agent1_datatypes if d != 'general'])})")

        # Agent 2 분석
        analysis_text.append(f"\n🔹 **컨텍스트 신뢰도 (Agent 2 - {result.context_risk_score:.0f}/100)**")
        if result.context_risk_score <= 30:
            analysis_text.append("   - 높은 신뢰도 사용자 (임원/관리층)")
        elif result.context_risk_score <= 50:
            analysis_text.append("   - 중간 신뢰도 사용자 (일반 직원)")
        else:
            analysis_text.append("   - 낮은 신뢰도 사용자 (외부/신규인력)")

        # Agent 3 분석
        analysis_text.append(f"\n🔹 **정책 위반 위험 (Agent 3 - {result.policy_risk_score:.0f}/100)**")
        if not result.policy_violation_detected:
            analysis_text.append("   - ✅ 정책 준수, 법령 위반 없음")
        else:
            analysis_text.append(f"   - ⚠️ 정책 위반 감지")

            # 위반 조항 상세 표시
            if hasattr(result, 'violated_sections') and result.violated_sections:
                analysis_text.append("   - **위반 예상 조항:**")
                seen_sections = set()
                for section in result.violated_sections:
                    key = (section.get('law'), section.get('article'))
                    if key not in seen_sections:
                        seen_sections.add(key)
                        law = section.get('law', '')
                        article = section.get('article', '')
                        title = section.get('title', '')
                        desc = section.get('desc', '')
                        analysis_text.append(f"     • {law} {article} ({title})")
                        analysis_text.append(f"       → {desc}")
            elif result.applicable_laws:
                analysis_text.append(f"   - 관련 법령: {', '.join(result.applicable_laws)}")

            if result.policy_risk_score <= 30:
                analysis_text.append("   - 경미한 위반 (관리자 검토 권장)")
            else:
                analysis_text.append("   - 심각한 위반 (승인 필수)")

        # 최종 평가
        analysis_text.append(f"\n⚖️ **최종 판정 (점수 계산)**")
        base_score = agent1_score * 0.4 + result.context_risk_score * 0.3
        analysis_text.append(f"   - 기본 점수 = 데이터({agent1_score:.0f}) × 0.4 + 컨텍스트({result.context_risk_score:.0f}) × 0.3 = {base_score:.1f}")

        if result.policy_violation_detected:
            violation_count = len(result.applicable_laws)
            multiplier = 1.0 + violation_count
            analysis_text.append(f"   - 정책 배수 = 1 + 위반법령({violation_count}개) = {multiplier}배")
            analysis_text.append(f"   - 최종 점수 = {base_score:.1f} × {multiplier} = {result.final_score:.1f}/100")
        else:
            analysis_text.append(f"   - 최종 점수 = {base_score:.1f} × 1 = {result.final_score:.1f}/100")

        analysis_text.append(f"   - **의사결정: {result.final_decision}**")

        st.write("\n".join(analysis_text))

        st.divider()
        st.markdown("**✅ 권장 조치**")

        rec_detail = {
            "Allow": ("✅ 승인 (안전한 요청)", "이 요청은 안전하며 즉시 처리할 수 있습니다."),
            "Conditional Allow": ("⚠️ 조건부 승인", "민감정보 마스킹 또는 접근 권한 확인 후 처리하세요."),
            "Approval Required": ("⏳ 관리자 승인 필요", "데이터나 정책 위반 위험이 있으니 관리자 검토 후 승인하세요."),
            "Block": ("🚫 차단 (거절)", "보안 정책 위반이 감지되었으므로 이 요청을 거부하세요.")
        }

        title, desc = rec_detail.get(result.final_decision, ("❓검토 필요", "상황을 재평가하세요"))
        st.info(f"**{title}**\n\n{desc}")

        # 상세 로그
        with st.expander("🔍 실행 로그"):
            st.code("\n".join([f"• {line}" for line in result.execution_log]), language="text")

st.divider()
st.markdown("**AI Security Gateway** | AAAI 2026 발표 예정")
