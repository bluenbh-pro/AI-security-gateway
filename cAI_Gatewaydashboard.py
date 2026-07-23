"""
AI Security Gateway - Streamlit Dashboard
Visualize agent operations and security decisions
"""

import streamlit as st
import json
from core.orchestrator import run_security_gateway
import pandas as pd

# Page config
st.set_page_config(
    page_title="AI Security Gateway",
    page_icon="shield",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title
st.title("AI Security Gateway Dashboard")
st.markdown("---")

# Sidebar: User Information
st.sidebar.header("User Information")

user_id = st.sidebar.text_input(
    "User ID",
    value="user_001",
    help="ID of the user requesting analysis"
)

department = st.sidebar.selectbox(
    "Department",
    ["Sales", "Finance", "Development", "HR", "Legal", "Other"],
    help="User's department"
)

role = st.sidebar.selectbox(
    "Role",
    ["employee", "lead", "manager", "admin"],
    help="User's role level"
)

request_hour = st.sidebar.slider(
    "Request Hour (24h)",
    min_value=0,
    max_value=23,
    value=14,
    step=1,
    help="Hour of request (0-23)"
)

# Main Content
st.header("Input Request")

# Text area for analysis
user_input = st.text_area(
    "Enter prompt to analyze",
    value="Analyze last quarter sales performance",
    height=150,
    placeholder="Enter text to be analyzed by LLM..."
)

# Buttons
col1, col2 = st.columns(2)

with col1:
    analyze_button = st.button("Run Analysis", use_container_width=True, type="primary")

with col2:
    st.write("")

# Run analysis
if analyze_button:
    with st.spinner("Analyzing..."):
        try:
            # Run orchestrator
            result = run_security_gateway(
                user_input=user_input,
                user_id=user_id,
                user_context={
                    "department": department,
                    "role": role,
                    "request_hour": request_hour
                }
            )

            # Display results
            st.markdown("---")
            st.header("Analysis Results")

            # Key metrics
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Decision", result["decision"])

            with col2:
                st.metric("Risk Score", f"{result['risk_score']:.1f} / 100")

            with col3:
                score = result["risk_score"]
                if score <= 20:
                    status = "SAFE"
                elif score <= 40:
                    status = "CAUTION"
                elif score <= 60:
                    status = "WARNING"
                elif score <= 80:
                    status = "CRITICAL"
                else:
                    status = "BLOCKED"

                st.metric("Status", status)

            # Decision description
            st.markdown("### Decision Explanation")

            decision_mapping = {
                "Allow": ("Safe", "Process original input"),
                "Conditional Allow": ("Caution", "Process with masking"),
                "Masking": ("Warning", "Apply forced masking"),
                "Approval Request": ("Critical", "Await admin approval"),
                "Block": ("Blocked", "Block + Log")
            }

            st.info(f"**{result['decision']}**: Processing request")

            # Agent logs
            st.markdown("### Agent Processing Logs")

            log_expander = st.expander("View Detailed Logs", expanded=True)
            with log_expander:
                for log in result.get("logs", []):
                    st.text(log)

            # JSON results
            st.markdown("### Full Results (JSON)")

            json_expander = st.expander("View JSON Details", expanded=False)
            with json_expander:
                st.json(result)

            # Success message
            if result.get("success"):
                st.success("Analysis completed successfully!")
            else:
                st.error("Error during analysis")

        except Exception as e:
            st.error(f"Error: {str(e)}")

# Footer
st.markdown("---")

col1, col2, col3 = st.columns(3)
with col1:
    st.caption("AI Security Gateway v1.0")
with col2:
    st.caption("5 Agent Integration")
with col3:
    st.caption("2026-06-23")

# Test cases
st.markdown("---")
st.markdown("### Test Cases")

test_cases = pd.DataFrame({
    "Test Name": [
        "Normal Request",
        "Sensitive Data",
        "SQL Injection",
        "Off-hours Access"
    ],
    "Example Input": [
        "Analyze last quarter sales",
        "Account number 1234567890",
        "SELECT * FROM users WHERE id=1 OR '1'='1'",
        "After-hours critical request"
    ],
    "Expected Risk": [
        "Low (0-20)",
        "High (41-60)",
        "Critical (81-100)",
        "Medium (21-40)"
    ]
})

st.dataframe(test_cases, use_container_width=True)
