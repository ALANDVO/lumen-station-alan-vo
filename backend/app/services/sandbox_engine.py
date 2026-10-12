"""Core sandboxing engine for tool output execution and token optimization."""

import os
import subprocess
import time
import uuid
from datetime import datetime, timezone
from typing import Tuple, Dict, Any, Optional

from app.core.config import settings
from app.core.database import get_db
from app.services.search_index import estimate_tokens, index_execution_chunks
from app.services.lifecycle_manager import register_process, unregister_process, terminate_process_tree


def fold_large_output(
    content: str,
    execution_id: str,
    head_lines_count: int = 25,
    tail_lines_count: int = 25,
) -> Tuple[str, int, int]:
    """
    Deterministically fold large terminal / tool outputs, preserving crucial head and tail contexts.
    Returns (compact_output, omitted_lines_count, omitted_bytes_count).
    """
    lines = content.splitlines(keepends=True)
    total_lines = len(lines)
    threshold = head_lines_count + tail_lines_count

    if total_lines <= threshold:
        return content, 0, 0

    head_part = "".join(lines[:head_lines_count])
    tail_part = "".join(lines[-tail_lines_count:])
    omitted_lines = lines[head_lines_count:-tail_lines_count]
    omitted_text = "".join(omitted_lines)
    omitted_bytes = len(omitted_text.encode("utf-8"))
    omitted_tokens = estimate_tokens(omitted_text)

    fold_banner = (
        f"\n\n... [Lumen Station Sandboxed: Omitted {len(omitted_lines)} lines "
        f"({omitted_bytes} bytes / ~{omitted_tokens} tokens). "
        f"Full output preserved in SQLite FTS5 (execution_id: {execution_id})] ...\n\n"
    )

    compact_text = head_part + fold_banner + tail_part
    return compact_text, len(omitted_lines), omitted_bytes


def execute_sandboxed_command(
    session_id: str,
    command: str,
    working_dir: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
    head_lines: int = 25,
    tail_lines: int = 25,
) -> Dict[str, Any]:
    """
    Execute tool command under hard wall-clock budget and sandbox output to minimize token consumption.
    """
    execution_id = str(uuid.uuid4())
    budget_timeout = timeout_seconds or settings.default_execution_timeout
    start_time = time.perf_counter()
    now_iso = datetime.now(timezone.utc).isoformat()

    cwd = working_dir or "."
    if not os.path.isdir(cwd):
        cwd = "."

    proc = None
    timed_out = False
    raw_output = ""
    exit_code = None
    status_str = "completed"
    error_msg = None

    try:
        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=cwd,
            start_new_session=True,
            bufsize=1,
            errors="replace",
        )
        register_process(execution_id, proc)

        try:
            raw_output, _ = proc.communicate(timeout=budget_timeout)
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            status_str = "timeout"
            terminate_process_tree(proc)
            try:
                partial_out, _ = proc.communicate(timeout=1.0)
                raw_output = partial_out or ""
            except Exception:
                raw_output = ""
            error_msg = f"Execution exceeded hard timeout budget of {budget_timeout} seconds."
            exit_code = -1
    except Exception as exc:
        status_str = "error"
        error_msg = str(exc)
        exit_code = -1
    finally:
        unregister_process(execution_id)

    duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

    # Cap maximum stored output to prevent runaway memory exhaustion
    if len(raw_output) > settings.max_output_bytes:
        raw_output = raw_output[:settings.max_output_bytes] + "\n... [TRUNCATED DUE TO MAX OUTPUT CAP] ..."

    raw_bytes = len(raw_output.encode("utf-8"))
    raw_tokens = estimate_tokens(raw_output)

    compact_output, omitted_lines, omitted_bytes = fold_large_output(
        content=raw_output,
        execution_id=execution_id,
        head_lines_count=head_lines,
        tail_lines_count=tail_lines,
    )

    compact_bytes = len(compact_output.encode("utf-8"))
    compact_tokens = estimate_tokens(compact_output)

    if raw_tokens > 0:
        savings_ratio = round(max(0.0, (raw_tokens - compact_tokens) / float(raw_tokens)), 4)
    else:
        savings_ratio = 0.0

    # Persist execution record and index chunks
    with get_db() as conn:
        # Verify session exists, or auto-create fallback
        session_row = conn.execute("SELECT id FROM sessions WHERE id = ?;", (session_id,)).fetchone()
        if not session_row:
            conn.execute("""
                INSERT INTO sessions (id, platform, working_dir, os_name, quiet_mode, created_at, updated_at)
                VALUES (?, 'unknown', ?, 'linux', 0, ?, ?);
            """, (session_id, cwd, now_iso, now_iso))

        conn.execute("""
            INSERT INTO executions (
                id, session_id, command, exit_code, duration_ms, raw_bytes, raw_tokens,
                compact_bytes, compact_tokens, savings_ratio, status, error, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            execution_id, session_id, command, exit_code, duration_ms, raw_bytes, raw_tokens,
            compact_bytes, compact_tokens, savings_ratio, status_str, error_msg, now_iso
        ))

        # Index chunks in FTS5
        index_execution_chunks(conn, execution_id, raw_output)

    return {
        "id": execution_id,
        "session_id": session_id,
        "command": command,
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "raw_bytes": raw_bytes,
        "raw_tokens": raw_tokens,
        "compact_bytes": compact_bytes,
        "compact_tokens": compact_tokens,
        "savings_ratio": savings_ratio,
        "status": status_str,
        "compact_output": compact_output,
        "raw_output": raw_output,
        "error": error_msg,
        "created_at": now_iso,
    }


def get_execution_detail(execution_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve full execution record including chunks count."""
    with get_db() as conn:
        row = conn.execute("""
            SELECT e.*, COUNT(c.id) as chunk_count
            FROM executions e
            LEFT JOIN execution_chunks c ON e.id = c.execution_id
            WHERE e.id = ?
            GROUP BY e.id;
        """, (execution_id,)).fetchone()

        if not row:
            return None

        # Reconstruct raw output from chunks
        chunk_rows = conn.execute("""
            SELECT content FROM execution_chunks
            WHERE execution_id = ?
            ORDER BY chunk_index ASC;
        """, (execution_id,)).fetchall()

        reconstructed_raw = "".join(c["content"] for c in chunk_rows)

        compact_output, _, _ = fold_large_output(reconstructed_raw, execution_id)

        return {
            "id": row["id"],
            "session_id": row["session_id"],
            "command": row["command"],
            "exit_code": row["exit_code"],
            "duration_ms": row["duration_ms"],
            "raw_bytes": row["raw_bytes"],
            "raw_tokens": row["raw_tokens"],
            "compact_bytes": row["compact_bytes"],
            "compact_tokens": row["compact_tokens"],
            "savings_ratio": row["savings_ratio"],
            "status": row["status"],
            "compact_output": compact_output,
            "raw_output": reconstructed_raw,
            "error": row["error"],
            "created_at": row["created_at"],
            "chunk_count": row["chunk_count"],
        }
