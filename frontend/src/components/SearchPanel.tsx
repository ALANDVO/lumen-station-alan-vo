import React, { useState } from "react";
import { api } from "../api/client";
import { SearchResponse, SearchResultItem } from "../types";

interface SearchPanelProps {
  selectedSessionId: string;
}

export const SearchPanel: React.FC<SearchPanelProps> = ({ selectedSessionId }) => {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [selectedChunk, setSelectedChunk] = useState<{ id: string; content: string } | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setSelectedChunk(null);

    try {
      const res = await api.searchChunks(query, selectedSessionId || undefined);
      setResults(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  const handleInspectChunk = async (chunkId: string) => {
    try {
      const res = await fetch(`/api/search/chunks/${chunkId}`, {
        headers: { Accept: "application/json" },
      });
      const data = await res.json();
      setSelectedChunk({ id: chunkId, content: data.content });
    } catch {
      setError("Failed to fetch chunk details");
    }
  };

  return (
    <div className="card">
      <div className="card-title">
        <span>SQLite FTS5 Output Chunk Search</span>
        <span className="badge badge-cyan">Sub-millisecond Retrieval</span>
      </div>

      <p style={{ fontSize: "0.85rem", color: "#94a3b8", marginBottom: "1rem" }}>
        Full text search across all folded and omitted command lines. Inspect individual chunks without re-running long commands.
      </p>

      {error && <div className="error-banner">{error}</div>}

      <form onSubmit={handleSearch} style={{ display: "flex", gap: "0.75rem", marginBottom: "1.5rem" }}>
        <input
          type="text"
          className="form-input"
          placeholder="Search errors, file paths, test failures, or symbols..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ flex: 1 }}
        />
        <button type="submit" disabled={loading} className="btn btn-primary">
          {loading ? "Searching..." : "Search FTS5"}
        </button>
      </form>

      {results && (
        <div>
          <div style={{ fontSize: "0.9rem", color: "#94a3b8", marginBottom: "1rem" }}>
            Found {results.total_matches} matched chunks for query &ldquo;<strong>{results.query}</strong>&rdquo;
          </div>

          {results.results.length === 0 ? (
            <div className="empty-state">No matching chunks found in the current scope.</div>
          ) : (
            <div className="table-responsive">
              <table>
                <thead>
                  <tr>
                    <th>Execution ID</th>
                    <th>Chunk Index</th>
                    <th>Tokens</th>
                    <th>Snippet Highlight</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {results.results.map((item: SearchResultItem) => (
                    <tr key={item.chunk_id}>
                      <td style={{ fontFamily: "monospace", fontSize: "0.8rem", color: "#94a3b8" }}>
                        {item.execution_id.slice(0, 8)}...
                      </td>
                      <td>{item.chunk_index}</td>
                      <td>{item.token_count}</td>
                      <td
                        style={{ fontFamily: "monospace", fontSize: "0.85rem", color: "#38bdf8" }}
                        dangerouslySetInnerHTML={{ __html: item.snippet }}
                      />
                      <td>
                        <button
                          className="btn btn-secondary"
                          style={{ padding: "0.2rem 0.5rem", fontSize: "0.75rem" }}
                          onClick={() => handleInspectChunk(item.chunk_id)}
                        >
                          View Chunk
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {selectedChunk && (
        <div style={{ marginTop: "1.5rem", padding: "1rem", background: "var(--bg-secondary)", borderRadius: "0.375rem", border: "1px solid var(--border-color)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
            <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>Chunk Content ({selectedChunk.id.slice(0, 8)})</span>
            <button
              className="btn btn-secondary"
              style={{ padding: "0.2rem 0.5rem", fontSize: "0.75rem" }}
              onClick={() => setSelectedChunk(null)}
            >
              Close
            </button>
          </div>
          <div className="terminal-box" style={{ maxHeight: "250px" }}>
            {selectedChunk.content}
          </div>
        </div>
      )}
    </div>
  );
};
