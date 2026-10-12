"""Data validation models for Lumen Station."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class SessionCreate(BaseModel):
    platform: str = Field(..., description="Target coding agent platform (e.g. claude-code, codex-cli, opencode, antigravity, pi)")
    working_dir: str = Field(default=".", description="Target workspace directory")
    os_name: str = Field(default="linux", description="Operating system name")
    quiet_mode: bool = Field(default=False, description="Disable injected routing framing to avoid auto-mode classifier triggers")


class SessionResponse(BaseModel):
    id: str
    platform: str
    working_dir: str
    os_name: str
    quiet_mode: bool
    created_at: str
    updated_at: str


class ExecutionRequest(BaseModel):
    session_id: str
    command: str = Field(..., description="Command or tool call to execute")
    working_dir: Optional[str] = Field(default=None, description="Optional working directory override")
    timeout_seconds: Optional[int] = Field(default=30, description="Hard wall-clock timeout budget for entire execution and indexing")
    head_lines: int = Field(default=25, description="Number of leading lines to preserve in compact summary")
    tail_lines: int = Field(default=25, description="Number of trailing lines to preserve in compact summary")


class ExecutionResponse(BaseModel):
    id: str
    session_id: str
    command: str
    exit_code: Optional[int]
    duration_ms: float
    raw_bytes: int
    raw_tokens: int
    compact_bytes: int
    compact_tokens: int
    savings_ratio: float
    status: str
    compact_output: str
    error: Optional[str] = None
    created_at: str


class ExecutionDetail(ExecutionResponse):
    raw_output: Optional[str] = None
    chunk_count: int = 0


class SearchQuery(BaseModel):
    query: str = Field(..., description="Full text search terms")
    session_id: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=50)


class SearchResultItem(BaseModel):
    chunk_id: str
    execution_id: str
    chunk_index: int
    chunk_type: str
    snippet: str
    token_count: int


class SearchResponse(BaseModel):
    query: str
    total_matches: int
    results: List[SearchResultItem]


class GuidanceRequest(BaseModel):
    session_id: str
    session_mode: Optional[str] = Field(default="default", description="Active agent session mode (e.g. default, investigate, refactor)")


class GuidanceResponse(BaseModel):
    session_id: str
    platform: str
    injected_block: str
    is_quiet_mode: bool
    framing_safety_status: str
    guidance_notes: List[str]


class CostComparisonItem(BaseModel):
    model_config = {"protected_namespaces": ()}
    model_name: str
    standard_cost_usd: float
    sandboxed_cost_usd: float
    saved_cost_usd: float


class SessionAnalytics(BaseModel):
    session_id: str
    platform: str
    total_executions: int
    raw_tokens: int
    compact_tokens: int
    saved_tokens: int
    savings_percentage: float
    duration_total_ms: float


class GlobalAnalytics(BaseModel):
    total_sessions: int
    total_executions: int
    raw_tokens_sum: int
    compact_tokens_sum: int
    saved_tokens_sum: int
    overall_savings_percentage: float
    models_comparison: List[CostComparisonItem]
    part_whole_invariant_verified: bool


class AdvisoryExplanationRequest(BaseModel):
    execution_id: str
    focus: Optional[str] = Field(default="summary", description="Focus area (e.g. failure_cause, diff_summary, security_implications)")


class AdvisoryExplanationResponse(BaseModel):
    execution_id: str
    provider: str
    model: str
    is_advisory: bool = True
    grounding_record_id: str
    explanation: str
    raw_prompt_tokens: int
    raw_completion_tokens: int


class AuditLogItem(BaseModel):
    id: str
    user_email: str
    action: str
    resource_type: str
    resource_id: str
    details: Dict[str, Any]
    created_at: str


class UserProfile(BaseModel):
    email: str
    role: str
    is_demo: bool = False
