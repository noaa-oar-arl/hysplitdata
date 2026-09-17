"""Verification module for HYSPLIT concentration dump files.

Provides mass conservation diagnostics, plume integrity checks,
and temporal plume dynamics analysis.
"""

from .config import VerificationConfig

__all__ = [
    "VerificationConfig",
    "VerificationRunner",
    "VerificationResults",
]


def VerificationRunner():  # type: ignore[misc]
    """Lazy-import VerificationRunner to avoid pulling in matplotlib/pandas."""
    raise NotImplementedError(
        "Import from hysplitdata.verify.runner directly: "
        "from hysplitdata.verify.runner import VerificationRunner"
    )


def VerificationResults():  # type: ignore[misc]
    """Lazy-import VerificationResults to avoid pulling in pandas."""
    raise NotImplementedError(
        "Import from hysplitdata.verify.runner directly: "
        "from hysplitdata.verify.runner import VerificationResults"
    )
