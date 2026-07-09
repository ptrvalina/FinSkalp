from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ComplianceCaseCreate(BaseModel):
    case_ref: str = Field(..., min_length=1, max_length=128)
    investigation_id: Optional[UUID] = None


class ComplianceCaseRead(BaseModel):
    id: UUID
    case_ref: str
    status: str
    investigation_id: Optional[UUID] = None
    fusion_result: Optional[dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class BankFeedBatchIn(BaseModel):
    schema_version: str = Field(..., pattern=r"^regulator-hub/v1$")
    hub_id: Optional[str] = None
    exported_at: Optional[str] = None
    feeds: List[dict[str, Any]]


class FuseCaseRequest(BaseModel):
    licensed_events: List[dict[str, Any]] = Field(default_factory=list)
    control_purchases: List[dict[str, Any]] = Field(default_factory=list)
    scenario_id: Optional[str] = Field(
        None, description="Demo scenario for licensed/control + on-chain adapters"
    )


class WalletScreenRequest(BaseModel):
    address: str = Field(..., min_length=1, max_length=128)
    chain: Optional[str] = Field(
        None, description="Optional explicit chain: btc, eth, tron"
    )
    depth: int = Field(1, ge=1, le=2)
    limit: int = Field(50, ge=1, le=100)


class WalletScreenResultRead(BaseModel):
    screening_id: str
    address: str
    chain: str
    risk_score: float
    risk_level: str
    confidence: float
    summary_ru: str
    findings: List[dict[str, Any]]
    evidence_chain: List[str]
    source_status: dict[str, str]
    onchain_summary: dict[str, Any]
    recommendations_ru: List[str]
    limitations_ru: List[str]


class FusionResultRead(BaseModel):
    case_ref: str
    attributions: List[dict[str, Any]]
    bridges: List[dict[str, Any]]
    linkage_scores: List[float]
    graph_stats: dict[str, int]


class FusionRunRead(BaseModel):
    id: UUID
    case_id: UUID
    celery_task_id: Optional[str] = None
    status: str
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    correlation_id: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class FusionAsyncResponse(BaseModel):
    run_id: UUID
    task_id: str
    status: str = "pending"


class RegulatorReportRead(BaseModel):
    case_ref: str
    scenario_title_ru: str
    generated_at: str
    executive_summary_ru: str
    illegal_flow_score: float
    risk_level: str
    findings: List[dict[str, Any]]
    attributions: List[dict[str, Any]]
    bridges: List[dict[str, Any]]
    metrics: dict[str, Any]
    evidence_graph: dict[str, int]


class DemoScenarioRead(BaseModel):
    id: str
    title_ru: str
    description_ru: str
    case_ref: str


class RegistryImportResult(BaseModel):
    imported: int
    total_in_db: int


class ScalpelCollectRequest(BaseModel):
    address: str = Field(..., min_length=1, max_length=128)
    chain: str = Field("tron", description="btc | eth | tron")
    depth: int = Field(2, ge=1, le=3)
    counterparties: List[str] = Field(default_factory=list)
    usernames: List[str] = Field(default_factory=list)


class ScalpelAsyncResponse(BaseModel):
    task_id: str
    status: str = "queued"


class ScalpelTaskStatus(BaseModel):
    task_id: str
    status: str
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class MaigretScanRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    top_sites: int = Field(120, ge=10, le=3000)
    use_tor: bool = False


class SpiderFootScanRequest(BaseModel):
    target: str = Field(..., min_length=1, max_length=256)
    modules: List[str] = Field(default_factory=list)


class OCRExtractResponse(BaseModel):
    filename: str
    backend: str
    text_chars: int
    confidence: float
    seizure_fields: dict[str, Any]
    entities: dict[str, Any]
    suitable_for_seizure_report: bool
    warnings: List[str] = Field(default_factory=list)


class LiveFusionRequest(BaseModel):
    address: str = Field(..., min_length=1, max_length=128)
    chain: str = Field("tron", description="btc | tron")
    max_hops: int = Field(3, ge=1, le=3)
    async_mode: bool = False
    case_ref: Optional[str] = None
    idempotency_key: Optional[str] = None


class ComplianceAuditLogRead(BaseModel):
    id: UUID
    case_id: Optional[UUID] = None
    actor_id: Optional[UUID] = None
    action: str
    payload: Optional[dict[str, Any]] = None
    correlation_id: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class LiveFusionAsyncResponse(BaseModel):
    task_id: str
    status: str = "queued"
    idempotency_key: Optional[str] = None


class ScoringPredictRequest(BaseModel):
    graph: dict[str, Any] = Field(default_factory=dict)
    address: str = ""
    chain: str = "tron"


class ScoringLabelCaseRequest(BaseModel):
    case_ref: str = ""
    address: str = ""
    chain: str = "tron"
    label: str = "illicit"
    risk_score: float = 0.0
    features: Optional[dict[str, Any]] = None
    source: str = "CASE_SAR"


class LiveCollectRequest(BaseModel):
    collector: str = Field(..., description="collect_tron_chain | collect_tron_trc20_transfers | …")
    address: Optional[str] = None
    query: Optional[str] = None
    username: Optional[str] = None
    async_mode: bool = False


class ComplianceCaseListItem(BaseModel):
    id: UUID
    case_ref: str
    status: str
    investigation_id: Optional[UUID] = None
    workflow_status: str = "new"
    assignee_id: Optional[UUID] = None
    priority: str = "normal"
    due_at: Optional[datetime] = None
    sla_breached: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CaseTransitionRequest(BaseModel):
    workflow_status: str = Field(..., pattern="^(new|triage|investigating|pending_filing|filed|archived)$")
    assignee_id: Optional[UUID] = None
    priority: Optional[str] = Field(None, pattern="^(low|normal|high|critical)$")


class CaseCommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)


class CaseCommentRead(BaseModel):
    id: UUID
    case_id: UUID
    author_id: UUID
    body: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class BatchScreenJobRead(BaseModel):
    id: UUID
    status: str
    total: int
    processed: int
    summary: Optional[dict[str, Any]] = None
    results: Optional[list] = None
    celery_task_id: Optional[str] = None
    created_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WatchlistSubscribeRequest(BaseModel):
    address: str = Field(..., min_length=1, max_length=128)
    chain: str = Field("tron", pattern="^(btc|eth|tron)$")
    label: Optional[str] = None


class WatchlistSubscriptionRead(BaseModel):
    id: UUID
    address: str
    chain: str
    label: Optional[str] = None
    active: bool
    last_checked_at: Optional[datetime] = None
    last_hit_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WebhookRegisterRequest(BaseModel):
    bank_id: str = Field(..., min_length=2, max_length=64)
    secret: str = Field(..., min_length=16, max_length=256)
    outbound_url: Optional[str] = None


class WebhookRegisterResponse(BaseModel):
    bank_id: str
    secret_hint: str
    enabled: bool

