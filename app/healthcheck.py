"""Container health check: validate outputs and the local Streamlit process."""
from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import urlopen
from pathlib import Path

from app.runtime_health import check_dashboard_health


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    result = check_dashboard_health(ROOT)
    try:
        with urlopen("http://127.0.0.1:8501/_stcore/health", timeout=2) as response:
            if response.status == 200:
                result["process"] = "alive"
            else:
                result["process"] = "unhealthy"
                result["errors"].append("Streamlit health endpoint returned a non-success status.")
                result["status"] = "unhealthy"
    except (URLError, TimeoutError, OSError):
        result["process"] = "unhealthy"
        result["errors"].append("Streamlit health endpoint did not respond.")
        result["status"] = "unhealthy"
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 1 if result["status"] == "unhealthy" else 0


if __name__ == "__main__":
    raise SystemExit(main())
