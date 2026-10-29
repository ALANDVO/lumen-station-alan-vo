"""Platform adapter configuration endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List

from app.core.security import require_role
from app.services.platform_adapters import (
    generate_platform_adapter,
    list_supported_platforms,
    register_platform_session,
    PLATFORM_SPECS,
)

router = APIRouter(prefix="/api/platform-adapters", tags=["platform-adapters"])


@router.get("", response_model=List[Dict[str, Any]])
def get_supported_platforms(
    user: Dict[str, Any] = Depends(require_role("viewer")),
) -> List[Dict[str, Any]]:
    """List all supported platforms with their capabilities."""
    return list_supported_platforms()


@router.get("/{platform}", response_model=Dict[str, Any])
def get_platform_adapter(
    platform: str,
    server_url: str = "http://127.0.0.1:8000",
    quiet_mode: bool = False,
    target_os: str = "linux",
    user: Dict[str, Any] = Depends(require_role("viewer")),
) -> Dict[str, Any]:
    """Generate platform adapter configuration for a specific platform and OS."""
    if platform not in PLATFORM_SPECS:
        raise HTTPException(status_code=404, detail=f"Unknown platform: {platform}")
    return generate_platform_adapter(platform, server_url, quiet_mode, target_os)


@router.post("/register", response_model=Dict[str, Any])
def create_platform_session(
    platform: str,
    working_dir: str = ".",
    os_name: str = "linux",
    quiet_mode: bool = False,
    user: Dict[str, Any] = Depends(require_role("operator")),
) -> Dict[str, Any]:
    """Register a new platform session with adapter configuration."""
    return register_platform_session(platform, working_dir, os_name, quiet_mode)
