import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "../App";
import { Header } from "../components/Header";
import { SearchPanel } from "../components/SearchPanel";
import { UserProfile } from "../types";

describe("Lumen Station Frontend Dashboard", () => {
  beforeEach(() => {
    // Mock global fetch for API client
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/api/auth/me")) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              email: "operator@lumen.local",
              role: "operator",
              is_demo: true,
              csrf_token: "mock-csrf-token",
            }),
        });
      }
      if (url.includes("/api/sessions")) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve([
              {
                id: "sess-test-1",
                platform: "claude-code",
                working_dir: ".",
                os_name: "linux",
                quiet_mode: false,
                created_at: "2026-10-12T15:00:00Z",
                updated_at: "2026-10-12T15:00:00Z",
              },
            ]),
        });
      }
      if (url.includes("/api/analytics/global")) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              total_sessions: 1,
              total_executions: 5,
              raw_tokens_sum: 5000,
              compact_tokens_sum: 200,
              saved_tokens_sum: 4800,
              overall_savings_percentage: 96.0,
              models_comparison: [
                {
                  model_name: "Claude 3.7 Sonnet",
                  standard_cost_usd: 0.015,
                  sandboxed_cost_usd: 0.0006,
                  saved_cost_usd: 0.0144,
                },
              ],
              part_whole_invariant_verified: true,
            }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
      });
    }) as any;
  });

  it("renders Header with application title and user role", () => {
    const mockUser: UserProfile = {
      email: "test-operator@lumen.local",
      role: "operator",
      is_demo: true,
      csrf_token: "test-token",
    };

    render(
      <Header
        user={mockUser}
        onLogout={vi.fn()}
        onDemoSwitchRole={vi.fn()}
      />
    );

    expect(screen.getByText("Lumen Station")).toBeDefined();
    expect(screen.getByText("test-operator@lumen.local")).toBeDefined();
    expect(screen.getByText("operator")).toBeDefined();
    expect(screen.getByText("Demo Mode")).toBeDefined();
  });

  it("renders full dashboard navigation and switches tabs", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("Lumen Station")).toBeDefined();
    });

    expect(screen.getByText("Tool Sandbox")).toBeDefined();
    expect(screen.getByText("FTS5 Search")).toBeDefined();
    expect(screen.getByText("Session Guidance")).toBeDefined();
    expect(screen.getByText("Token Economics")).toBeDefined();
    expect(screen.getByText("Audit Log")).toBeDefined();

    // Switch to FTS5 Search tab
    fireEvent.click(screen.getByText("FTS5 Search"));
    expect(screen.getByText("SQLite FTS5 Output Chunk Search")).toBeDefined();

    // Switch to Token Economics tab
    fireEvent.click(screen.getByText("Token Economics"));
    expect(screen.getByText("Global Token Economics & Invariant Validation")).toBeDefined();
  });

  it("renders SearchPanel with interactive query input", () => {
    render(<SearchPanel selectedSessionId="sess-test-1" />);

    expect(screen.getByPlaceholderText(/Search errors, file paths/i)).toBeDefined();
    expect(screen.getByText("Search FTS5")).toBeDefined();
  });
});
