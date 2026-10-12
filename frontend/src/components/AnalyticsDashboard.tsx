import React, { useState } from "react";
import { api } from "../api/client";
import { GlobalAnalytics, CostComparisonItem } from "../types";

interface AnalyticsDashboardProps {
  analytics: GlobalAnalytics | null;
  onRefresh: () => void;
}

export const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({ analytics, onRefresh }) => {
  const [exporting, setExporting] = useState(false);

  const handleExport = async () => {
    setExporting(true);
    try {
      const data = await api.exportSnapshot();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `lumen-station-analytics-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Failed to export analytics snapshot");
    } finally {
      setExporting(false);
    }
  };

  if (!analytics) {
    return <div className="loading-indicator">Loading token savings analytics...</div>;
  }

  return (
    <div>
      <div className="card">
        <div className="card-title">
          <span>Global Token Economics & Invariant Validation</span>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button className="btn btn-secondary" onClick={onRefresh}>
              Refresh
            </button>
            <button className="btn btn-primary" disabled={exporting} onClick={handleExport}>
              {exporting ? "Exporting..." : "Export Snapshot"}
            </button>
          </div>
        </div>

        <div className="grid-cols-4" style={{ marginBottom: "1.5rem" }}>
          <div className="metric-card">
            <div className="metric-value" style={{ color: "#06b6d4" }}>
              {analytics.overall_savings_percentage.toFixed(1)}%
            </div>
            <div className="metric-label">Context Reduction</div>
          </div>
          <div className="metric-card">
            <div className="metric-value">{analytics.saved_tokens_sum.toLocaleString()}</div>
            <div className="metric-label">Tokens Kept Out</div>
          </div>
          <div className="metric-card">
            <div className="metric-value">{analytics.total_executions}</div>
            <div className="metric-label">Total Executions</div>
          </div>
          <div className="metric-card">
            <div
              className="metric-value"
              style={{
                color: analytics.part_whole_invariant_verified ? "#10b981" : "#f43f5e",
                fontSize: "1.25rem",
              }}
            >
              {analytics.part_whole_invariant_verified ? "VERIFIED (OK)" : "VIOLATION"}
            </div>
            <div className="metric-label">Part-Whole Invariant (#950)</div>
          </div>
        </div>

        <div style={{ fontSize: "0.95rem", fontWeight: 600, color: "#f8fafc", marginBottom: "0.75rem" }}>
          Frontier Model Counterfactual Cost Comparison
        </div>

        <div className="table-responsive">
          <table>
            <thead>
              <tr>
                <th>Model Tier</th>
                <th>Raw Tool Cost (USD)</th>
                <th>Sandboxed Cost (USD)</th>
                <th>Net Cost Saved (USD)</th>
              </tr>
            </thead>
            <tbody>
              {analytics.models_comparison.map((item: CostComparisonItem) => (
                <tr key={item.model_name}>
                  <td style={{ fontWeight: 600 }}>{item.model_name}</td>
                  <td>${item.standard_cost_usd.toFixed(4)}</td>
                  <td>${item.sandboxed_cost_usd.toFixed(4)}</td>
                  <td style={{ color: "#10b981", fontWeight: 600 }}>
                    +${item.saved_cost_usd.toFixed(4)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
