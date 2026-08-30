"""Opt-in upload helper for S3-compatible HTTP endpoints."""

from pathlib import Path
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def upload_archive(archive: Path, endpoint: str, token_env: str = "CODESAVER_CLOUD_TOKEN") -> int:
    """Upload one ZIP with a bearer token and return the HTTP status code."""
    token = os.environ.get(token_env)
    if not token:
        raise ValueError(f"Environment variable {token_env} is not set")
    request = Request(endpoint.rstrip("/") + "/" + archive.name, data=archive.read_bytes(), method="PUT")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Content-Type", "application/zip")
    try:
        with urlopen(request, timeout=60) as response:
            return response.status
    except (HTTPError, URLError, OSError) as exc:
        raise RuntimeError(f"Cloud upload failed: {exc}") from exc
