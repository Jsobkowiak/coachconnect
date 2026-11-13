"""Expose shared auth helpers when checks are executed directly."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "support"))
from auth import authenticated_context, credentials, install_http_auth  # noqa: E402,F401
