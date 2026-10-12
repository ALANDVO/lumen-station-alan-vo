"""Tests for process lifecycle management and orphan guards."""

import subprocess
import time
import pytest
from app.services.lifecycle_manager import (
    abort_execution,
    terminate_process_tree,
    is_parent_alive,
    register_process,
    unregister_process,
)


def test_lifecycle_abort_nonexistent():
    """Verify aborting an unknown process returns False."""
    assert abort_execution("nonexistent-execution-uuid") is False


def test_parent_death_detection_guard():
    """Verify parent death detection check logic."""
    # Under regular test execution, os.getppid() should be alive
    assert is_parent_alive() is True
    # PID 99999999 is definitely not alive
    assert is_parent_alive(99999999) is False


def test_terminate_process_tree():
    """Verify clean process termination of child subprocess."""
    proc = subprocess.Popen(["sleep", "10"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    assert proc.poll() is None

    success = terminate_process_tree(proc, timeout_grace_seconds=0.5)
    assert success is True
    assert proc.poll() is not None
