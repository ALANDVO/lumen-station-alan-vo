import React, { useState, useEffect } from "react";
import { api } from "./api/client";
import { UserProfile, SessionItem, GlobalAnalytics } from "./types";
import { Header } from "./components/Header";
import { ExecutionSandbox } from "./components/ExecutionSandbox";
import { SearchPanel } from "./components/SearchPanel";
import { SessionGuidance } from "./components/SessionGuidance";
import { AnalyticsDashboard } from "./components/AnalyticsDashboard";
import { AuditLogView } from "./components/AuditLogView";

export const App: React.FC = () => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string>("");
  const [analytics, setAnalytics] = useState<GlobalAnalytics | null>(null);
  const [activeTab, setActiveTab] = useState<"sandbox" | "search" | "sessions" | "analytics" | "audit">("sandbox");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    initializeApp();
  }, []);

  const initializeApp = async () => {
    setLoading(true);
    setError(null);
    try {
      let profile: UserProfile;
      try {
        profile = await api.getProfile();
      } catch {
        // Fallback to local demo operator login
        profile = await api.loginDemo("operator");
      }
      setUser(profile);

      await reloadData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const reloadData = async () => {
    try {
      const sessList = await api.getSessions();
      setSessions(sessList);
      if (sessList.length > 0 && !selectedSessionId) {
        setSelectedSessionId(sessList[0].id);
      }
      const analyticsData = await api.getGlobalAnalytics();
      setAnalytics(analyticsData);
    } catch {
      // Background reload failure handled gracefully
    }
  };

  const handleLogout = async () => {
    await api.logout();
    setUser(null);
    initializeApp();
  };

  const handleDemoSwitchRole = async (role: "viewer" | "operator" | "admin") => {
    const profile = await api.loginDemo(role);
    setUser(profile);
  };

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div className="loading-indicator">Initializing Lumen Station Proxy...</div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Header
        user={user}
        onLogout={handleLogout}
        onDemoSwitchRole={handleDemoSwitchRole}
      />

      <main className="container" style={{ flex: 1, paddingBottom: "2rem" }}>
        {error && <div className="error-banner">{error}</div>}

        <nav className="nav-tabs" aria-label="Dashboard Navigation">
          <button
            className={`tab-btn ${activeTab === "sandbox" ? "active" : ""}`}
            onClick={() => setActiveTab("sandbox")}
          >
            Tool Sandbox
          </button>
          <button
            className={`tab-btn ${activeTab === "search" ? "active" : ""}`}
            onClick={() => setActiveTab("search")}
          >
            FTS5 Search
          </button>
          <button
            className={`tab-btn ${activeTab === "sessions" ? "active" : ""}`}
            onClick={() => setActiveTab("sessions")}
          >
            Session Guidance
          </button>
          <button
            className={`tab-btn ${activeTab === "analytics" ? "active" : ""}`}
            onClick={() => setActiveTab("analytics")}
          >
            Token Economics
          </button>
          <button
            className={`tab-btn ${activeTab === "audit" ? "active" : ""}`}
            onClick={() => setActiveTab("audit")}
          >
            Audit Log
          </button>
        </nav>

        {activeTab === "sandbox" && (
          <ExecutionSandbox
            sessions={sessions}
            selectedSessionId={selectedSessionId}
            onSelectSession={setSelectedSessionId}
            onExecutionCompleted={reloadData}
          />
        )}

        {activeTab === "search" && (
          <SearchPanel selectedSessionId={selectedSessionId} />
        )}

        {activeTab === "sessions" && (
          <SessionGuidance
            sessions={sessions}
            selectedSessionId={selectedSessionId}
            onSessionCreated={reloadData}
            onSelectSession={setSelectedSessionId}
          />
        )}

        {activeTab === "analytics" && (
          <AnalyticsDashboard
            analytics={analytics}
            onRefresh={reloadData}
          />
        )}

        {activeTab === "audit" && (
          <AuditLogView />
        )}
      </main>

      <footer style={{ borderTop: "1px solid var(--border-color)", padding: "1.25rem 0", textAlign: "center", fontSize: "0.8rem", color: "#64748b" }}>
        Lumen Station &copy; 2026 Alan Vo &lt;alanvo@gmail.com&gt;. Provider-agnostic AI agent context optimization.
      </footer>
    </div>
  );
};

export default App;
