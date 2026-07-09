"""FastAPI microservice for ONNX risk inference."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from flowsint_crypto_compliance.ml.onnx_inference import ONNXRiskScorer, default_model_path
from flowsint_crypto_compliance.ml.scoring_pipeline import score_risk

app = FastAPI(title="FinSkalp ML Scoring", version="1.0.0")
_scorer = ONNXRiskScorer()


class ScoreRequest(BaseModel):
    address: str
    chain: str = "tron"
    mentions: list[dict[str, Any]] = Field(default_factory=list)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "onnx_available": _scorer.available,
        "model_path": str(default_model_path()),
    }


@app.post("/score")
def score(body: ScoreRequest) -> dict[str, Any]:
    class _M:
        def __init__(self, d: dict[str, Any]) -> None:
            self.confidence = d.get("confidence", 0.5)
            self.source_type = d.get("source_type", "")
            self.risk_tag = d.get("risk_tag", "")

    mentions = [_M(m) for m in body.mentions]
    return score_risk(body.address, body.chain, mentions)


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8891)
