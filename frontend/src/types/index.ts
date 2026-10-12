export interface UserProfile {
  email: string;
  role: "viewer" | "operator" | "admin";
  is_demo: boolean;
  csrf_token: string;
}

export interface SessionItem {
  id: string;
  platform: string;
  working_dir: string;
  os_name: string;
  quiet_mode: boolean;
  execution_count?: number;
  created_at: string;
  updated_at: string;
}

export interface ExecutionResponse {
  id: string;
  session_id: string;
  command: string;
  exit_code: number | null;
  duration_ms: number;
  raw_bytes: number;
  raw_tokens: number;
  compact_bytes: number;
  compact_tokens: number;
  savings_ratio: number;
  status: "completed" | "timeout" | "error";
  compact_output: string;
  raw_output?: string;
  error?: string | null;
  created_at: string;
  chunk_count?: number;
}

export interface SearchResultItem {
  chunk_id: string;
  execution_id: string;
  chunk_index: number;
  chunk_type: string;
  snippet: string;
  token_count: number;
}

export interface SearchResponse {
  query: string;
  total_matches: number;
  results: SearchResultItem[];
}

export interface GuidanceResponse {
  session_id: string;
  platform: string;
  injected_block: string;
  is_quiet_mode: boolean;
  framing_safety_status: string;
  guidance_notes: string[];
}

export interface CostComparisonItem {
  model_name: string;
  standard_cost_usd: number;
  sandboxed_cost_usd: number;
  saved_cost_usd: number;
}

export interface GlobalAnalytics {
  total_sessions: number;
  total_executions: number;
  raw_tokens_sum: number;
  compact_tokens_sum: number;
  saved_tokens_sum: number;
  overall_savings_percentage: number;
  models_comparison: CostComparisonItem[];
  part_whole_invariant_verified: boolean;
}

export interface AuditLogItem {
  id: string;
  user_email: string;
  action: string;
  resource_type: string;
  resource_id: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface AdvisoryExplanationResponse {
  execution_id: string;
  provider: string;
  model: string;
  is_advisory: boolean;
  grounding_record_id: string;
  explanation: string;
  raw_prompt_tokens: number;
  raw_completion_tokens: number;
}
