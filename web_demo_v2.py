#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI Security Gateway - FastAPI Web Demo V2
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import sys
import os

# 절대 경로 설정
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 신선한 import
from core.orchestrator import run_security_gateway

app = FastAPI(title="AI Security Gateway Demo")

class AnalysisRequest(BaseModel):
    user_input: str
    user_id: str = "user_001"
    department: str = "Sales"
    role: str = "employee"
    request_hour: int = 14

@app.get("/", response_class=HTMLResponse)
async def root():
    return """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>AI Security Gateway</title>
<style>
body { font-family: Arial; background: #f0f0f0; padding: 20px; }
.container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }
h1 { color: #333; }
.input-group { margin: 15px 0; }
label { display: block; font-weight: bold; margin-bottom: 5px; }
input, select, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-family: Arial; }
button { background: #667eea; color: white; padding: 12px 30px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
button:hover { background: #5568d3; }
.result { margin-top: 30px; padding: 20px; background: #f9f9f9; border-left: 4px solid #667eea; }
.risk-low { color: #28a745; font-size: 24px; font-weight: bold; }
.risk-high { color: #dc3545; font-size: 24px; font-weight: bold; }
.risk-medium { color: #ffc107; font-size: 24px; font-weight: bold; }
</style>
</head>
<body>
<div class="container">
<h1>AI Security Gateway</h1>

<div class="input-group">
<label>Prompt:</label>
<textarea id="input" rows="4">고객의 주민등록번호 알수 있어?</textarea>
</div>

<div class="input-group">
<label>Department:</label>
<select id="dept">
<option>Sales</option>
<option>Finance</option>
<option>Development</option>
<option>HR</option>
</select>
</div>

<button onclick="analyze()">Analyze</button>

<div id="result"></div>
</div>

<script>
async function analyze() {
    const input = document.getElementById('input').value;
    const dept = document.getElementById('dept').value;

    try {
        const resp = await fetch('/analyze', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                user_input: input,
                user_id: 'user_001',
                department: dept,
                role: 'employee',
                request_hour: 14
            })
        });

        const data = await resp.json();
        const score = data.risk_score;
        const riskClass = score < 21 ? 'risk-low' : score < 61 ? 'risk-medium' : 'risk-high';

        document.getElementById('result').innerHTML = `
            <div class="result">
            <div class="${riskClass}">Risk Score: ${score.toFixed(1)} / 100</div>
            <p><strong>Decision:</strong> ${data.decision}</p>
            <p><strong>Action:</strong> ${data.action}</p>
            </div>
        `;
    } catch (e) {
        alert('Error: ' + e.message);
    }
}
</script>
</body>
</html>"""

@app.post("/analyze")
async def analyze(request: AnalysisRequest):
    result = run_security_gateway(
        user_input=request.user_input,
        user_id=request.user_id,
        user_context={
            "department": request.department,
            "role": request.role,
            "request_hour": request.request_hour
        }
    )
    return result

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*70)
    print("[AI Security Gateway - Web Demo V2]")
    print("="*70)
    print("[*] Open your browser: http://localhost:8000")
    print("="*70 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
