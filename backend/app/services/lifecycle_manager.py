"""Process lifecycle management, cancellation tokens, and orphan prevention."""

import os
import signal
import subprocess
import threading
import time
from typing import Dict, Optional, Any

# In-flight active processes mapping execution_id -> subprocess.Popen
_ACTIVE_PROCESSES: Dict[str, subprocess.Popen] = {}
_PROCESS_LOCK = threading.Lock()


def register_process(execution_id: str, proc: subprocess.Popen) -> None:
    """Register an in-flight process for cancellation tracking."""
    with _PROCESS_LOCK:
        _ACTIVE_PROCESSES[execution_id] = proc


def unregister_process(execution_id: str) -> None:
    """Unregister finished process."""
    with _PROCESS_LOCK:
        _ACTIVE_PROCESSES.pop(execution_id, None)


def abort_execution(execution_id: str) -> bool:
    """Abort an in-flight execution process tree cleanly."""
    with _PROCESS_LOCK:
        proc = _ACTIVE_PROCESSES.get(execution_id)
    if not proc:
        return False

    return terminate_process_tree(proc)


def terminate_process_tree(proc: subprocess.Popen, timeout_grace_seconds: float = 1.5) -> bool:
    """
    Terminate a process and its child tree cleanly.
    Sends SIGTERM, waits grace period, then escalates to SIGKILL if still running.
    """
    if proc.poll() is not None:
        return True

    try:
        # If process is its own group leader (start_new_session=True), terminate group
        if hasattr(os, "killpg") and hasattr(os, "getpgid"):
            try:
                pgid = os.getpgid(proc.pid)
                if pgid == proc.pid:
                    os.killpg(pgid, signal.SIGTERM)
                else:
                    proc.terminate()
            except (ProcessLookupError, PermissionError):
                proc.terminate()
        else:
            proc.terminate()

        # Wait grace period
        start_time = time.time()
        while time.time() - start_time < timeout_grace_seconds:
            if proc.poll() is not None:
                return True
            time.sleep(0.05)

        # Escalate to kill
        if hasattr(os, "killpg") and hasattr(os, "getpgid"):
            try:
                pgid = os.getpgid(proc.pid)
                if pgid == proc.pid:
                    os.killpg(pgid, signal.SIGKILL)
                else:
                    proc.kill()
            except (ProcessLookupError, PermissionError):
                proc.kill()
        else:
            proc.kill()

        proc.wait(timeout=1.0)
        return True
    except Exception:
        return False


def is_parent_alive(parent_pid: Optional[int] = None) -> bool:
    """
    Check if parent process is still alive.
    Used for parent-death detection guards on long-running workers.
    """
    ppid = parent_pid or os.getppid()
    if ppid <= 1:
        return False
    try:
        os.kill(ppid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False
