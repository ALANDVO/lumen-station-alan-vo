import React, { useState } from "react";
import { api } from "../api/client";
import { ExecutionResponse, SessionItem, AdvisoryExplanationResponse } from "../types";

interface ExecutionSandboxProps {
  sessions: SessionItem[];
  selectedSessionId: string;
  onSelectSession: (id: string) => void;
  onExecutionCompleted: () => void;
}

export const ExecutionSandbox: React.FC<ExecutionSandboxProps> = ({
  sessions,
  selectedSessionId,
  onSelectSession,
  onExecutionCompleted,
}) => {
  const [command, setCommand] = useState("pytest -v");
  const [timeoutSec, setTimeoutSec] = useState(30);
  const [headLines, setHeadLines] = useState(25);
  const [tailLines, setTailLines] = useState(25);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [execution, setExecution] = useState<ExecutionResponse | null>(null);
  const [showRaw, setShowRaw] = useState(false);
  const [advisory, setAdvisory] = useState<AdvisoryExplanationResponse | null>(null);
  const [explaining, setExplaining] = useState(false);

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSessionId) {
      setError("Please select or create an active agent session first.");
      return;
    }

    setLoading(true);
    setError(null);
    setAdvisory(null);

    try {
      const res = await api.executeCommand({
        session_id: selectedSessionId,
        command,
        timeout_seconds: timeoutSec,
        head_lines: headLines,
        tail_lines: tailLines,
      });
      setExecution(res);
      onExecutionCompleted();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleAbort = async () => {
    if (!execution?.id) return;
    try {
      await api.abortExecution(execution.id);
      setError("Active process aborted.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleExplain = async (focus: string) => {
    if (!execution?.id) return;
    setExplaining(true);
    try {
      const exp = await api.explainExecution(execution.id, focus);
      setAdvisory(exp);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setExplaining(false);
    }
  };

  return (
    <div>
      <div className="card">
        <div className="card-title">
          <span>Tool Execution & Output Sandboxing Engine</span>
          <span className="badge badge-emerald">Deterministic Proxy</span>
        </div>

        {error && <div className="error-banner">{error}</div>}

        <form onSubmit={handleRun}>
          <div className="grid-cols-2">
            <div className="form-group">
              <label className="form-label">Active Agent Session</label>
              <select
                className="form-select"
                value={selectedSessionId}
                onChange={(e) => onSelectSession(e.target.value)}
              >
                <option value="">-- Select Agent Session --</option>
                {sessions.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.platform} ({s.id.slice(0, 8)}) {s.quiet_mode ? "[Quiet Mode]" : ""}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Command to Sandbox</label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. pytest, git diff, npm test, find ."
                value={command}
                onChange={(e) => setCommand(e.target.value)}
              />
            </div>
          </div>

          <div className="grid-cols-4" style={{ marginBottom: "1rem" }}>
            <div className="form-group">
              <label className="form-label">Timeout Budget (s)</label>
              <input
                type="number"
                min="1"
                max="300"
                className="form-input"
                value={timeoutSec}
                onChange={(e) => setTimeoutSec(Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Head Lines Preserved</label>
              <input
                type="number"
                min="5"
                max="100"
                className="form-input"
                value={headLines}
                onChange={(e) => setHeadLines(Number(e.target.value))}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Tail Lines Preserved</label>
              <input
                type="number"
                min="5"
                max="100"
                className="form-input"
                value={tailLines}
                onChange={(e) => setTailLines(Number(e.target.value))}
              />
            </div>
            <div style={{ display: "flex", alignItems: "flex-end", gap: "0.5rem", marginBottom: "1rem" }}>
              <button
                type="submit"
                disabled={loading}
                className="btn btn-primary"
                style={{ flex: 1 }}
              >
                {loading ? "Running..." : "Sandbox Execute"}
              </button>
              {loading && (
                <button
                  type="button"
                  className="btn btn-danger"
                  onClick={handleAbort}
                >
                  Abort
                </button>
              )}
            </div>
          </div>
        </form>
      </div>

      {execution && (
        <div className="card">
          <div className="card-title">
            <span>Sandboxed Execution Result</span>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button
                className="btn btn-secondary"
                style={{ padding: "0.25rem 0.5rem", fontSize: "0.8rem" }}
                onClick={() => setShowRaw(!showRaw)}
              >
                {showRaw ? "Show Compact Preview" : "Show Full Raw"}
              </button>
              <button
                className="btn btn-secondary"
                style={{ padding: "0.25rem 0.5rem", fontSize: "0.8rem" }}
                disabled={explaining}
                onClick={() => handleExplain("summary")}
              >
                {explaining ? "Analyzing..." : "Opt-in Advisory Summary"}
              </button>
            </div>
          </div>

          <div className="grid-cols-4" style={{ marginBottom: "1.25rem" }}>
            <div className="metric-card">
              <div className="metric-value" style={{ color: "#06b6d4" }}>
                {(execution.savings_ratio * 100).toFixed(1)}%
              </div>
              <div className="metric-label">Context Kept Out</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">
                {execution.compact_tokens}
                <span style={{ fontSize: "0.8rem", color: "#64748b", marginLeft: "4px" }}>
                  / {execution.raw_tokens}
                </span>
              </div>
              <div className="metric-label">Tokens (Compact / Raw)</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">{execution.duration_ms} ms</div>
              <div className="metric-label">Wall-Clock Latency</div>
            </div>
            <div className="metric-card">
              <div className="metric-value" style={{ color: execution.exit_code === 0 ? "#10b981" : "#f43f5e" }}>
                {execution.exit_code !== null ? execution.exit_code : "N/A"}
              </div>
              <div className="metric-label">Exit Code ({execution.status})</div>
            </div>
          </div>

          <div className="terminal-box">
            {showRaw ? (execution.raw_output || execution.compact_output) : execution.compact_output}
          </div>

          {advisory && (
            <div style={{ marginTop: "1rem", padding: "1rem", background: "rgba(99, 102, 241, 0.1)", border: "1px solid rgba(99, 102, 241, 0.3)", borderRadius: "0.375rem" }}>
              <div style={{ fontWeight: 600, color: "#818cf8", marginBottom: "0.25rem" }}>
                Advisory Explanation ({advisory.provider} - {advisory.model})
              </div>
              <p style={{ fontSize: "0.9rem", color: "#e2e8f0" }}>{advisory.explanation}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
