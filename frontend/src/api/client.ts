import {
  UserProfile,
  SessionItem,
  ExecutionResponse,
  SearchResponse,
  GuidanceResponse,
  GlobalAnalytics,
  AuditLogItem,
  AdvisoryExplanationResponse,
} from "../types";

let currentCsrfToken = "";

export function setCsrfToken(token: string): void {
  currentCsrfToken = token;
}

export function getCsrfToken(): string {
  return currentCsrfToken;
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set("Accept", "application/json");

  if (options.body && typeof options.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (currentCsrfToken && ["POST", "PUT", "PATCH", "DELETE"].includes(options.method || "GET")) {
    headers.set("X-CSRF-Token", currentCsrfToken);
  }

  const response = await fetch(path, {
    ...options,
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) {
        errorDetail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // Ignore JSON parse failure
    }
    throw new Error(errorDetail);
  }

  return response.json() as Promise<T>;
}

export const api = {
  // Auth
  async getProfile(): Promise<UserProfile> {
    const profile = await request<UserProfile>("/api/auth/me");
    if (profile.csrf_token) {
      setCsrfToken(profile.csrf_token);
    }
    return profile;
  },

  async loginDemo(role: string = "operator"): Promise<UserProfile> {
    const res = await request<UserProfile>("/api/auth/demo-login?role=" + role, {
      method: "POST",
    });
    return res;
  },

  async logout(): Promise<{ message: string }> {
    return request<{ message: string }>("/api/auth/logout", {
      method: "POST",
    });
  },

  // Sessions
  async getSessions(limit = 50): Promise<SessionItem[]> {
    return request<SessionItem[]>(`/api/sessions?limit=${limit}`);
  },

  async createSession(payload: {
    platform: string;
    working_dir: string;
    os_name: string;
    quiet_mode: boolean;
  }): Promise<SessionItem> {
    return request<SessionItem>("/api/sessions", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async getSessionGuidance(sessionId: string, sessionMode = "default"): Promise<GuidanceResponse> {
    return request<GuidanceResponse>("/api/sessions/guidance", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, session_mode: sessionMode }),
    });
  },

  // Sandbox Executions
  async executeCommand(payload: {
    session_id: string;
    command: string;
    working_dir?: string;
    timeout_seconds?: number;
    head_lines?: number;
    tail_lines?: number;
  }): Promise<ExecutionResponse> {
    return request<ExecutionResponse>("/api/sandbox/execute", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async getExecution(executionId: string): Promise<ExecutionResponse> {
    return request<ExecutionResponse>(`/api/sandbox/executions/${executionId}`);
  },

  async abortExecution(executionId: string): Promise<{ message: string }> {
    return request<{ message: string }>(`/api/sandbox/executions/${executionId}/abort`, {
      method: "POST",
    });
  },

  async explainExecution(executionId: string, focus = "summary"): Promise<AdvisoryExplanationResponse> {
    return request<AdvisoryExplanationResponse>(`/api/sandbox/executions/${executionId}/explain`, {
      method: "POST",
      body: JSON.stringify({ execution_id: executionId, focus }),
    });
  },

  // Search
  async searchChunks(query: string, sessionId?: string, limit = 10): Promise<SearchResponse> {
    return request<SearchResponse>("/api/search", {
      method: "POST",
      body: JSON.stringify({ query, session_id: sessionId || null, limit }),
    });
  },

  // Analytics & Audit
  async getGlobalAnalytics(): Promise<GlobalAnalytics> {
    return request<GlobalAnalytics>("/api/analytics/global");
  },

  async getAuditLogs(limit = 50, offset = 0): Promise<AuditLogItem[]> {
    return request<AuditLogItem[]>(`/api/analytics/audit-logs?limit=${limit}&offset=${offset}`);
  },

  async exportSnapshot(): Promise<Record<string, unknown>> {
    return request<Record<string, unknown>>("/api/analytics/export");
  },
};
