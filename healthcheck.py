"""
healthcheck.py
Docker HEALTHCHECK script.

Usage in Dockerfile:
  HEALTHCHECK CMD python healthcheck.py

Exit codes:
  0 — service healthy
  1 — service unhealthy
"""

import sys
import urllib.request
import urllib.error

HEALTH_URL = "http://localhost:8000/health"
TIMEOUT_SECONDS = 5


def main() -> None:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=TIMEOUT_SECONDS) as response:
            if response.status == 200:
                print("Healthcheck PASSED")
                sys.exit(0)
            else:
                print(f"Healthcheck FAILED — HTTP {response.status}")
                sys.exit(1)
    except (urllib.error.URLError, OSError) as exc:
        print(f"Healthcheck FAILED — {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
