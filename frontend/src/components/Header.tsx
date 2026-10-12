import React from "react";
import { UserProfile } from "../types";

interface HeaderProps {
  user: UserProfile | null;
  onLogout: () => void;
  onDemoSwitchRole: (role: "viewer" | "operator" | "admin") => void;
}

export const Header: React.FC<HeaderProps> = ({ user, onLogout, onDemoSwitchRole }) => {
  return (
    <header>
      <div className="container header-content">
        <div className="logo-area">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: "#06b6d4" }}>
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
          </svg>
          <div>
            <h1 style={{ fontSize: "1.25rem", fontWeight: 700, color: "#f8fafc" }}>
              Lumen Station
            </h1>
            <p style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
              AI Coding Agent Context Optimization Proxy
            </p>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
          {user && (
            <>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span className="badge badge-cyan">{user.role}</span>
                {user.is_demo && <span className="badge badge-amber">Demo Mode</span>}
                <span style={{ fontSize: "0.85rem", color: "#cbd5e1" }}>{user.email}</span>
              </div>

              {user.is_demo && (
                <select
                  className="form-select"
                  style={{ padding: "0.25rem 0.5rem", fontSize: "0.8rem", width: "auto" }}
                  value={user.role}
                  onChange={(e) => onDemoSwitchRole(e.target.value as "viewer" | "operator" | "admin")}
                >
                  <option value="operator">Role: Operator</option>
                  <option value="viewer">Role: Viewer</option>
                  <option value="admin">Role: Admin</option>
                </select>
              )}

              <button className="btn btn-secondary" style={{ padding: "0.3rem 0.75rem", fontSize: "0.8rem" }} onClick={onLogout}>
                Logout
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
};
