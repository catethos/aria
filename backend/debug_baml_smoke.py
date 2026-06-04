"""Run a minimal BAML/OpenRouter smoke test without report data.

This script is intentionally tiny: it sends only "hello baml" to the smoke
BAML function under debug_baml/baml_src. It is useful for distinguishing BAML
runtime issues from report-packet or prompt issues.
"""

from __future__ import annotations

import os

from env_loader import load_local_env


def main() -> None:
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        os.environ.pop(key, None)
    load_local_env(override=True)

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    print(
        {
            "openrouter_key_present": bool(api_key),
            "openrouter_key_length": len(api_key),
            "openrouter_key_prefix_ok": api_key.startswith("sk-or-"),
        }
    )

    from baml_smoke_client.baml_client.sync_client import b

    result = b.SmokeEcho("hello baml")
    print({"result_type": type(result).__name__, "message": result.message})


if __name__ == "__main__":
    main()
