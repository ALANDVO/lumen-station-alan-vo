import React, { useState, useEffect } from "react";
import { api } from "../api/client";
import { SessionItem, GuidanceResponse } from "../types";

interface SessionGuidanceProps {
  sessions: SessionItem[];
  selectedSessionId: string;
  onSessionCreated: () => void;
  onSelectSession: (id: string) => void;
}

export const SessionGuidance: React.FC<SessionGuidanceProps> = ({
  sessions,
  selectedSessionId,
  onSessionCreated,
  onSelectSession,
}) => {
  const [platform, setPlatform] = useState("claude-code");
  const [workingDir, setWorkingDir] = useState(".");
  const [quietMode, setQuietMode] = useState(false);
  const [sessionMode, setSessionMode] = useState("default");
  const [creating, setCreating] = useState(false);
  const [guidance, setGuidance] = useState<GuidanceResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (selectedSessionId) {
      loadGuidance(selectedSessionId, sessionMode);
    }
  }, [selectedSessionId, sessionMode]);

  const loadGuidance = async (sessId: string, mode: string) => {
    try {
      const res = await api.getSessionGuidance(sessId, mode);
      setGuidance(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      const sess = await api.createSession({
        platform,
        working_dir: workingDir,
        os_name: "linux",
        quiet_mode: quietMode,
      });
      onSessionCreated();
      onSelectSession(sess.id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setCreating(false);
    }
  };

  const handleCopyPrompt = () => {
    if (guidance?.injected_block) {
      navigator.clipboard.writeText(guidance.injected_block);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="grid-cols-2">
      <div className="card">
        <div className="card-title">
          <span>Agent Session Registration</span>
          <span className="badge badge-indigo">Multi-Platform</span>
        </div>

        {error && <div className="error-banner">{error}</div>}

        <form onSubmit={handleCreateSession}>
          <div className="form-group">
            <label className="form-label">Coding Agent Platform</label>
            <select
              className="form-select"
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
            >
              <option value="claude-code">Claude Code (Anthropic)</option>
              <option value="codex-cli">Codex CLI (OpenAI)</option>
              <option value="opencode">OpenCode V2</option>
              <option value="antigravity">Antigravity (Google)</option>
              <option value="pi">Pi Interactive</option>
              <option value="gemini-cli">Gemini CLI</option>
              <option value="vscode-copilot">VS Code Copilot</option>
              <option value="zed">Zed Editor</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Working Directory</label>
            <input
              type="text"
              className="form-input"
              value={workingDir}
              onChange={(e) => setWorkingDir(e.target.value)}
            />
          </div>

          <div className="form-group" style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <input
              type="checkbox"
              id="quietMode"
              checked={quietMode}
              onChange={(e) => setQuietMode(e.target.checked)}
            />
            <label htmlFor="quietMode" style={{ fontSize: "0.85rem", color: "#cbd5e1", cursor: "pointer" }}>
              Enable Quiet Mode (Zero injected prompt blocks, prevent auto-mode bypass triggers #911/#967)
            </label>
          </div>

          <button type="submit" disabled={creating} className="btn btn-primary" style={{ width: "100%" }}>
            {creating ? "Creating..." : "Register New Session"}
          </button>
        </form>

        <div style={{ marginTop: "1.5rem" }}>
          <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "#94a3b8", marginBottom: "0.5rem" }}>
            Existing Sessions ({sessions.length})
          </div>
          <div style={{ maxHeight: "180px", overflowY: "auto" }}>
            {sessions.map((s) => (
              <div
                key={s.id}
                onClick={() => onSelectSession(s.id)}
                style={{
                  padding: "0.5rem 0.75rem",
                  marginBottom: "0.25rem",
                  borderRadius: "0.25rem",
                  cursor: "pointer",
                  background: selectedSessionId === s.id ? "var(--bg-tertiary)" : "rgba(255,255,255,0.02)",
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: "0.85rem",
                }}
              >
                <span>{s.platform}</span>
                <span style={{ color: "#64748b", fontFamily: "monospace" }}>{s.id.slice(0, 8)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-title">
          <span>Safe Session Guidance Block</span>
          {guidance && (
            <span className={`badge ${guidance.is_quiet_mode ? "badge-amber" : "badge-emerald"}`}>
              {guidance.framing_safety_status}
            </span>
          )}
        </div>

        <div className="form-group">
          <label className="form-label">Session Mode</label>
          <select
            className="form-select"
            value={sessionMode}
            onChange={(e) => setSessionMode(e.target.value)}
          >
            <option value="default">Default Mode</option>
            <option value="investigate">Investigate Mode (Recursive scans)</option>
            <option value="refactor">Refactor Mode (Multi-file diffs)</option>
          </select>
        </div>

        {guidance ? (
          <div>
            <div className="terminal-box" style={{ minHeight: "160px", marginBottom: "1rem" }}>
              {guidance.is_quiet_mode
                ? "[Quiet Mode Active: No prompt block injected into agent transcript]"
                : guidance.injected_block}
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <button
                className="btn btn-secondary"
                disabled={guidance.is_quiet_mode}
                onClick={handleCopyPrompt}
              >
                {copied ? "Copied!" : "Copy Guidance Block"}
              </button>
              <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
                Attribution: <code>lumen-station-local</code>
              </div>
            </div>

            <ul style={{ marginTop: "1rem", fontSize: "0.8rem", color: "#94a3b8", paddingLeft: "1.2rem" }}>
              {guidance.guidance_notes.map((note, idx) => (
                <li key={idx}>{note}</li>
              ))}
            </ul>
          </div>
        ) : (
          <div className="empty-state">Select or create a session to generate guidance.</div>
        )}
      </div>
    </div>
  );
};
