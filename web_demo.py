"""
AI Security Gateway - FastAPI Web Demo
Simple web interface to visualize agent operations
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from core.orchestrator import run_security_gateway
import json

app = FastAPI(title="AI Security Gateway Demo")

class AnalysisRequest(BaseModel):
    user_input: str
    user_id: str = "user_001"
    department: str = "Sales"
    role: str = "employee"
    request_hour: int = 14

@app.get("/", response_class=HTMLResponse)
async def root():
    """Main dashboard page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>AI Security Gateway</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }

            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                overflow: hidden;
            }

            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px;
                text-align: center;
            }

            .header h1 {
                font-size: 2.5em;
                margin-bottom: 10px;
            }

            .header p {
                font-size: 1.1em;
                opacity: 0.9;
            }

            .content {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 30px;
                padding: 40px;
            }

            .section {
                display: flex;
                flex-direction: column;
            }

            .section h2 {
                color: #333;
                margin-bottom: 20px;
                font-size: 1.3em;
            }

            label {
                display: block;
                margin-bottom: 8px;
                color: #555;
                font-weight: 500;
            }

            input, select, textarea {
                width: 100%;
                padding: 12px;
                margin-bottom: 15px;
                border: 1px solid #ddd;
                border-radius: 6px;
                font-size: 1em;
                font-family: inherit;
            }

            textarea {
                min-height: 120px;
                resize: vertical;
            }

            button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 14px 30px;
                border: none;
                border-radius: 6px;
                font-size: 1.1em;
                cursor: pointer;
                transition: transform 0.2s, box-shadow 0.2s;
                margin-top: 10px;
            }

            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            }

            button:active {
                transform: translateY(0);
            }

            #results {
                grid-column: 1 / -1;
                display: none;
            }

            #results.show {
                display: block;
            }

            .result-card {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 15px;
                border-left: 4px solid #667eea;
            }

            .metric {
                display: flex;
                justify-content: space-between;
                padding: 15px;
                background: white;
                margin-bottom: 10px;
                border-radius: 6px;
                border: 1px solid #eee;
            }

            .metric-label {
                font-weight: 600;
                color: #555;
            }

            .metric-value {
                font-size: 1.2em;
                color: #667eea;
                font-weight: bold;
            }

            .decision {
                font-size: 1.5em;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                color: white;
                margin-bottom: 15px;
            }

            .decision.allow {
                background: #28a745;
            }

            .decision.caution {
                background: #ffc107;
                color: #333;
            }

            .decision.warning {
                background: #ff9800;
            }

            .decision.critical {
                background: #e74c3c;
            }

            .decision.block {
                background: #c0392b;
            }

            .logs {
                background: #1e1e1e;
                color: #d4d4d4;
                padding: 15px;
                border-radius: 6px;
                font-family: 'Monaco', 'Courier New', monospace;
                font-size: 0.9em;
                max-height: 300px;
                overflow-y: auto;
                margin-top: 10px;
            }

            .log-item {
                margin-bottom: 8px;
                padding: 8px;
                border-left: 3px solid #667eea;
                padding-left: 12px;
            }

            .test-cases {
                grid-column: 1 / -1;
                margin-top: 20px;
            }

            .test-case {
                background: #f8f9fa;
                padding: 15px;
                margin-bottom: 10px;
                border-radius: 6px;
                cursor: pointer;
                transition: all 0.2s;
                border: 1px solid #ddd;
            }

            .test-case:hover {
                background: #e8edf5;
                border-color: #667eea;
            }

            .test-case h4 {
                color: #667eea;
                margin-bottom: 8px;
            }

            .test-case p {
                color: #666;
                font-size: 0.95em;
            }

            .loading {
                display: none;
                text-align: center;
                padding: 20px;
                color: #667eea;
            }

            .loading.show {
                display: block;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔐 AI 보안 게이트웨이</h1>
                <p>실시간 LLM 보안 분석 대시보드</p>
            </div>

            <div class="content">
                <div class="section">
                    <h2>👤 사용자 정보</h2>
                    <label>사용자 ID:</label>
                    <input type="text" id="userId" value="user_001">

                    <label>부서:</label>
                    <select id="department">
                        <option>영업팀</option>
                        <option>재무팀</option>
                        <option>개발팀</option>
                        <option>인사팀</option>
                        <option>법무팀</option>
                        <option>마케팅팀</option>
                        <option>CS팀</option>
                    </select>

                    <label>직급:</label>
                    <select id="role">
                        <option value="employee">직원</option>
                        <option value="lead">리드</option>
                        <option value="manager">매니저</option>
                        <option value="admin">관리자</option>
                    </select>

                    <label>요청 시간 (0-23):</label>
                    <input type="range" id="requestHour" min="0" max="23" value="14">
                    <span id="hourDisplay">14:00</span>
                </div>

                <div class="section">
                    <h2>📝 분석할 프롬프트</h2>
                    <textarea id="userInput" placeholder="분석할 프롬프트를 입력하세요...">지난 분기 판매 현황 분석해줘</textarea>
                    <button onclick="analyzePrompt()">🔍 분석</button>
                </div>

                <div id="results">
                    <h2>📊 분석 결과</h2>
                    <div id="decision"></div>
                    <div id="metrics"></div>
                    <div>
                        <h3>🤖 에이전트 처리 로그:</h3>
                        <div class="logs" id="logs"></div>
                    </div>
                </div>

                <div class="test-cases">
                    <h2>📚 테스트 케이스</h2>
                    <div class="test-case" onclick="testCase('일반 요청', '지난 분기 판매 현황을 분석해줘')">
                        <h4>✅ 일반 요청</h4>
                        <p>예상: 낮은 위험도 (허용)</p>
                    </div>
                    <div class="test-case" onclick="testCase('민감한 데이터', '고객 박철수의 계좌번호는 1234567890입니다')">
                        <h4>⚠️ 민감한 데이터</h4>
                        <p>예상: 높은 위험도 (마스킹)</p>
                    </div>
                    <div class="test-case" onclick="testCase('SQL 주입 공격', \"SELECT * FROM users WHERE id=1 OR '1'='1'\")">
                        <h4>🚨 기술 공격</h4>
                        <p>예상: 매우 높음 (차단)</p>
                    </div>
                    <div class="test-case" onclick="setHourAndAnalyze(23, '야간 시간에 모든 거래 기록을 내려받고 싶습니다')">
                        <h4>🌙 야간 접근</h4>
                        <p>예상: 중간~높은 위험도</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="loading" id="loading">
            ⏳ 분석 중입니다... 잠시만 기다려주세요.
        </div>

        <script>
            // Update hour display
            document.getElementById('requestHour').addEventListener('input', function() {
                const hour = parseInt(this.value);
                document.getElementById('hourDisplay').textContent = String(hour).padStart(2, '0') + ':00';
            });

            function translateAction(action) {
                const actions = {
                    'allow': '허용',
                    'conditional': '조건부허용',
                    'mask': '마스킹',
                    'approval_request': '승인요청',
                    'block': '차단',
                    'process': '처리 중'
                };
                return actions[action] || action;
            }

            function testCase(name, input) {
                document.getElementById('userInput').value = input;
                analyzePrompt();
            }

            function setHourAndAnalyze(hour, input) {
                document.getElementById('requestHour').value = hour;
                document.getElementById('hourDisplay').textContent = String(hour).padStart(2, '0') + ':00';
                document.getElementById('userInput').value = input;
                analyzePrompt();
            }

            async function analyzePrompt() {
                const userInput = document.getElementById('userInput').value;
                const userId = document.getElementById('userId').value;
                const department = document.getElementById('department').value;
                const role = document.getElementById('role').value;
                const requestHour = parseInt(document.getElementById('requestHour').value);

                if (!userInput.trim()) {
                    alert('분석할 프롬프트를 입력하세요');
                    return;
                }

                document.getElementById('loading').classList.add('show');
                document.getElementById('results').classList.remove('show');

                try {
                    const response = await fetch('/analyze', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            user_input: userInput,
                            user_id: userId,
                            department: department,
                            role: role,
                            request_hour: requestHour
                        })
                    });

                    const data = await response.json();

                    // Display decision
                    const score = data.risk_score;
                    let decisionClass = 'allow';
                    if (score > 20 && score <= 40) decisionClass = 'caution';
                    else if (score > 40 && score <= 60) decisionClass = 'warning';
                    else if (score > 60 && score <= 80) decisionClass = 'critical';
                    else if (score > 80) decisionClass = 'block';

                    document.getElementById('decision').innerHTML = `
                        <div class="decision ${decisionClass}">
                            <strong>${data.decision}</strong>
                        </div>
                    `;

                    // Display metrics
                    document.getElementById('metrics').innerHTML = `
                        <div class="metric">
                            <span class="metric-label">위험도 점수:</span>
                            <span class="metric-value">${score.toFixed(1)} / 100</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">조치:</span>
                            <span class="metric-value">${translateAction(data.action)}</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">상태:</span>
                            <span class="metric-value">${data.success ? '✅ 성공' : '❌ 오류'}</span>
                        </div>
                    `;

                    // Display logs
                    const logsHtml = data.logs.map(log =>
                        `<div class="log-item">${log}</div>`
                    ).join('');
                    document.getElementById('logs').innerHTML = logsHtml;

                    document.getElementById('results').classList.add('show');
                    document.getElementById('loading').classList.remove('show');

                } catch (error) {
                    alert('오류: ' + error.message);
                    document.getElementById('loading').classList.remove('show');
                }
            }
        </script>
    </body>
    </html>
    """

@app.post("/analyze")
async def analyze(request: AnalysisRequest):
    """Analyze a prompt and return security assessment"""
    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*70)
    print("[AI Security Gateway - Web Demo]")
    print("="*70)
    print("[*] Open your browser and go to: http://localhost:8000")
    print("="*70 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
