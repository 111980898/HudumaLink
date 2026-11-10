"""Smoke-test a deployed Huduma Link URL before promotion."""

import json
import os
import sys
from urllib.request import urlopen

BASE_URL = os.environ.get("HUDUMALINK_URL", "https://huduma-link-nine.vercel.app").rstrip("/")
ROUTES = ("/", "/login", "/register", "/track", "/_app/health")


def main() -> int:
    for route in ROUTES:
        with urlopen(f"{BASE_URL}{route}", timeout=30) as response:
            print(f"{route}: {response.status}")
            if response.status != 200:
                return 1
    with urlopen(f"{BASE_URL}/_app/health", timeout=30) as response:
        health = json.load(response)
    if health != {"service": "huduma-link", "status": "ok"}:
        print(f"Unexpected health response: {health}")
        return 1
    print(f"Production smoke test passed: {BASE_URL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
