import React, { useState, useEffect } from "react";
import { api } from "../api/client";
import { PlatformSpec, PlatformAdapterConfig } from "../types";

export const PlatformAdapters: React.FC = () => {
  const [platforms, setPlatforms] = useState<PlatformSpec[]>([]);
  const [selectedPlatform, setSelectedPlatform] = useState<string>("");
  const [adapterConfig, setAdapterConfig] = useState<PlatformAdapterConfig | null>(null);
  const [quietMode, setQuietMode] = useState(false);
  const [targetOs, setTargetOs] = useState<"linux" | "windows">("linux");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    loadPlatforms();
  }, []);

  const loadPlatforms = async () => {
    try {
      setLoading(true);
      const data = await api.getPlatforms();
      setPlatforms(data);
      if (data.length > 0 && !selectedPlatform) {
        setSelectedPlatform(data[0].platform);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const loadAdapterConfig = async () => {
    if (!selectedPlatform) return;
    try {
      setLoading(true);
      setError(null);
      const data = await api.getPlatformAdapter(selectedPlatform, quietMode, targetOs);
      setAdapterConfig(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAdapterConfig();
  }, [selectedPlatform, quietMode, targetOs]);

  const copyToClipboard = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(label);
      setTimeout(() => setCopied(null), 2000);
    } catch {
      setError("Failed to copy to clipboard");
    }
  };

  const formatJson = (obj: Record<string, unknown> | null) => {
    if (!obj) return "null";
    return JSON.stringify(obj, null, 2);
  };

  if (loading && platforms.length === 0) {
    return <div style={styles.container}>Loading platforms...</div>;
  }

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>Platform Adapters</h2>
      <p style={styles.subtitle}>
        Generate platform-specific hook configurations and parent-death guard scripts for AI coding agents.
      </p>

      {error && <div style={styles.error}>{error}</div>}

      <div style={styles.controls}>
        <div style={styles.controlGroup}>
          <label style={styles.label}>Platform:</label>
          <select
            style={styles.select}
            value={selectedPlatform}
            onChange={(e) => setSelectedPlatform(e.target.value)}
            disabled={loading}
          >
            {platforms.map((p) => (
              <option key={p.platform} value={p.platform}>
                {p.display_name} ({p.platform})
              </option>
            ))}
          </select>
        </div>

        <div style={styles.controlGroup}>
          <label style={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={quietMode}
              onChange={(e) => setQuietMode(e.target.checked)}
              disabled={loading}
              style={styles.checkbox}
            />
            Quiet Mode
          </label>
        </div>

        <div style={styles.controlGroup}>
          <label style={styles.label}>Target OS:</label>
          <select
            style={styles.select}
            value={targetOs}
            onChange={(e) => setTargetOs(e.target.value as "linux" | "windows")}
            disabled={loading}
          >
            <option value="linux">Linux / macOS</option>
            <option value="windows">Windows</option>
          </select>
        </div>
      </div>

      {adapterConfig && (
        <div style={sections.container}>
          <div style={sections.section}>
            <div style={sections.sectionHeader}>
              <h3 style={sections.sectionTitle}>Configuration ({adapterConfig.platform})</h3>
              <button
                style={styles.copyButton}
                onClick={() => copyToClipboard(formatJson(adapterConfig.configuration), "configuration")}
                disabled={loading}
              >
                {copied === "configuration" ? "Copied!" : "Copy JSON"}
              </button>
            </div>
            <pre style={styles.codeBlock}>{formatJson(adapterConfig.configuration)}</pre>
          </div>

          {adapterConfig.parent_death_guard_script_unix && (
            <div style={sections.section}>
              <div style={sections.sectionHeader}>
                <h3 style={sections.sectionTitle}>Parent-Death Guard (Unix/Linux/macOS)</h3>
                <button
                  style={styles.copyButton}
                  onClick={() => copyToClipboard(adapterConfig.parent_death_guard_script_unix!, "unix-script")}
                  disabled={loading}
                >
                  {copied === "unix-script" ? "Copied!" : "Copy Script"}
                </button>
              </div>
              <pre style={styles.codeBlock}>{adapterConfig.parent_death_guard_script_unix}</pre>
            </div>
          )}

          {adapterConfig.parent_death_guard_script_windows && (
            <div style={sections.section}>
              <div style={sections.sectionHeader}>
                <h3 style={sections.sectionTitle}>Parent-Death Guard (Windows PowerShell)</h3>
                <button
                  style={styles.copyButton}
                  onClick={() => copyToClipboard(adapterConfig.parent_death_guard_script_windows!, "windows-script")}
                  disabled={loading}
                >
                  {copied === "windows-script" ? "Copied!" : "Copy Script"}
                </button>
              </div>
              <pre style={styles.codeBlock}>{adapterConfig.parent_death_guard_script_windows}</pre>
            </div>
          )}

          {adapterConfig.issues_addressed.length > 0 && (
            <div style={sections.section}>
              <h3 style={sections.sectionTitle}>Issues Addressed</h3>
              <ul style={styles.issuesList}>
                {adapterConfig.issues_addressed.map((issue, idx) => (
                  <li key={idx} style={styles.issueItem}>{issue}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: "24px",
    maxWidth: "1000px",
    margin: "0 auto",
  },
  title: {
    margin: "0 0 8px",
    fontSize: "28px",
    fontWeight: 600,
  },
  subtitle: {
    margin: "0 0 24px",
    color: "#666",
    fontSize: "16px",
  },
  error: {
    padding: "12px 16px",
    marginBottom: "16px",
    background: "#fee",
    border: "1px solid #fcc",
    borderRadius: "6px",
    color: "#c00",
  },
  controls: {
    display: "flex",
    gap: "24px",
    flexWrap: "wrap",
    alignItems: "flex-end",
    marginBottom: "24px",
    padding: "16px",
    background: "#fafafa",
    borderRadius: "8px",
    border: "1px solid #eee",
  },
  controlGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  label: {
    fontSize: "13px",
    fontWeight: 500,
    color: "#333",
  },
  select: {
    padding: "8px 12px",
    fontSize: "14px",
    border: "1px solid #ddd",
    borderRadius: "6px",
    background: "white",
    minWidth: "200px",
  },
  checkboxLabel: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    fontSize: "14px",
    cursor: "pointer",
  },
  checkbox: {
    width: "16px",
    height: "16px",
  },
  copyButton: {
    padding: "6px 12px",
    fontSize: "12px",
    background: "#0066cc",
    color: "white",
    border: "none",
    borderRadius: "4px",
    cursor: "pointer",
  },
  codeBlock: {
    padding: "16px",
    background: "#1e1e1e",
    color: "#d4d4d4",
    borderRadius: "6px",
    overflow: "auto",
    fontSize: "13px",
    lineHeight: "1.5",
    maxHeight: "400px",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  },
  issuesList: {
    paddingLeft: "20px",
    margin: 0,
  },
  issueItem: {
    marginBottom: "8px",
    lineHeight: "1.5",
  },
};

const sections: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column",
    gap: "24px",
  },
  section: {
    border: "1px solid #e0e0e0",
    borderRadius: "8px",
    overflow: "hidden",
  },
  sectionHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "12px 16px",
    background: "#f5f5f5",
    borderBottom: "1px solid #e0e0e0",
  },
  sectionTitle: {
    margin: 0,
    fontSize: "16px",
    fontWeight: 600,
  },
};

export default PlatformAdapters;
