"""
FastAPI 기반 REST API 서버

사용법:
    uvicorn api_server:app --reload --port 8000

엔드포인트:
    POST /analyze - 프롬프트 분석
    GET /health - 헬스체크
    GET /docs - 자동생성 문서

구현 상태: [TODO - W3 Day 15-17에서 구현]
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

from core.orchestrator import run_security_gateway

# ============================================================================
# [TODO] 구현 필요 부분:
# 1. FastAPI 앱 초기화
# 2. 요청/응답 모델 정의
# 3. 엔드포인트 구현
# ============================================================================

app = FastAPI(
    title="LLM 보안 게이트웨이 API",
    description="프롬프트 모니터링 및 데이터 보호 API",
    version="1.0.0"
)


# 요청/응답 모델
class AnalyzeRequest(BaseModel):
    """분석 요청"""
    prompt: str
    user_id: str = "anonymous"
    department: str = "미정"


class AnalyzeResponse(BaseModel):
    """분석 응답"""
    request_id: str
    timestamp: str
    decision: str
    risk_score: float
    output: str
    details: Optional[Dict[str, Any]] = None


# ============================================================================
# [TODO] 엔드포인트 구현
# ============================================================================


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_prompt(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    프롬프트 분석 엔드포인트

    [TODO] 구현 단계:
    1. 요청 유효성 검증
    2. run_security_gateway() 호출
    3. 응답 객체 생성
    4. 결과 반환

    예시:
    ```bash
    curl -X POST http://localhost:8000/analyze \\
      -H "Content-Type: application/json" \\
      -d '{
        "prompt": "고객 박철수의 계좌번호는 1234567890입니다",
        "user_id": "user_001",
        "department": "영업1팀"
      }'
    ```

    응답:
    ```json
    {
        "request_id": "req_xxx",
        "timestamp": "2026-06-09T14:30:00",
        "decision": "조건부허용",
        "risk_score": 35,
        "output": "고객 박철수의 계좌번호는 ****입니다"
    }
    ```
    """

    # [TODO] 구현
    try:
        result = run_security_gateway(
            user_input=request.prompt,
            user_id=request.user_id,
            user_context={"department": request.department}
        )

        return AnalyzeResponse(
            request_id="req_xxx",
            timestamp=datetime.utcnow().isoformat(),
            decision=result.get("decision", "허용"),
            risk_score=result.get("risk_score", 0),
            output=result.get("output", "")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """헬스체크"""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/")
async def root() -> Dict[str, str]:
    """루트 엔드포인트"""
    return {
        "name": "LLM 보안 게이트웨이 API",
        "docs": "/docs",
        "health": "/health"
    }


# [TODO] 추가 엔드포인트 (필요에 따라)
# @app.get("/logs") - 감사 로그 조회
# @app.post("/feedback") - 오탐지 피드백
# @app.get("/stats") - 통계 조회
# @app.post("/config/reload") - 설정 재로드


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
