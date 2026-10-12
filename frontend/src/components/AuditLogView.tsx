import React, { useState, useEffect } from "react";
import { api } from "../api/client";
import { AuditLogItem } from "../types";

export const AuditLogView: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadLogs();
  }, []);

  const loadLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await api.getAuditLogs(50);
      setLogs(items);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <div className="card-title">
        <span>Security & Execution Audit Trail</span>
        <button className="btn btn-secondary" onClick={loadLogs} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh Logs"}
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {logs.length === 0 ? (
        <div className="empty-state">No audit events recorded yet.</div>
      ) : (
        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Operator</th>
                <th>Action</th>
                <th>Resource</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id}>
                  <td style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                    {new Date(log.created_at).toLocaleTimeString()}
                  </td>
                  <td>{log.user_email}</td>
                  <td>
                    <span className="badge badge-indigo">{log.action}</span>
                  </td>
                  <td>
                    {log.resource_type}: {log.resource_id.slice(0, 8)}
                  </td>
                  <td style={{ fontFamily: "monospace", fontSize: "0.8rem", color: "#94a3b8" }}>
                    {JSON.stringify(log.details)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
