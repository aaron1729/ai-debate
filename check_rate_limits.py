#!/usr/bin/env python3
"""Inspect rate-limit usage stored in Redis via Upstash REST API."""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, List, Tuple

try:
    from upstash_redis import Redis
except ImportError:
    print("upstash-redis package not installed.\n" "Install with: pip install upstash-redis", file=sys.stderr)
    sys.exit(1)

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:  # python-dotenv optional
    load_dotenv = None  # type: ignore


def load_env(value: str) -> str:
    if not value:
        return ""
    expand = os.path.expandvars(value)
    expand = os.path.expanduser(expand)
    return expand


def get_client() -> "Redis":
    # Try loading .env if python-dotenv is available
    if load_dotenv is not None:
        env_path = Path(".env")
        if env_path.exists():
            load_dotenv(env_path)

    url = load_env(os.getenv("UPSTASH_REDIS_REST_URL", "")).strip()
    token = load_env(os.getenv("UPSTASH_REDIS_REST_TOKEN", "")).strip()

    if not url or not token:
        print(
            "Missing UPSTASH_REDIS_REST_URL / UPSTASH_REDIS_REST_TOKEN environment variables.\n"
            "Set them in the environment or install python-dotenv so check_rate_limits.py can load your .env file.",
            file=sys.stderr,
        )
        sys.exit(1)

    return Redis(url=url, token=token)


def build_keys(ip: str, include_global: bool) -> List[Tuple[str, str]]:
    models = ["claude", "gpt4", "gemini", "grok"]
    keys = []
    for model in models:
        handle = model
        keys.append((handle, f"ratelimit:usage:{ip}:{model}"))
        keys.append((f"{handle}-sliding", f"@upstash/ratelimit:{ip}:{model}"))
        if include_global:
            keys.append((f"{handle}-global-usage", f"ratelimit:usage-global:{model}"))
            keys.append((f"{handle}-global-sliding", f"@upstash/ratelimit:global:{model}"))
    return keys


def reset_keys(ip: str, include_global: bool) -> None:
    client = get_client()
    keys = [key for _, key in build_keys(ip, include_global)]

    if not keys:
        print("No keys to delete.")
        return

    deleted = client.delete(*keys)
    print(f"Deleted {deleted} keys for IP {ip}{' (including global backstop)' if include_global else ''}.")


def inspect(ip: str) -> None:
    client = get_client()
    models = ["claude", "gpt4", "gemini", "grok"]

    print(f"Inspecting rate limit usage for IP '{ip}'\n")

    for model in models:
        usage_key = f"ratelimit:usage:{ip}:{model}"
        sliding_key = f"@upstash/ratelimit:{ip}:{model}"
        global_key = f"ratelimit:usage-global:{model}"
        global_sliding_key = f"@upstash/ratelimit:global:{model}"

        usage_val: Any = None
        sliding_count: int = 0
        global_val: Any = None

        try:
            usage_val = client.get(usage_key)
        except Exception as err:  # noqa: BLE001
            print(f"  Failed to read {usage_key}: {err}")

        try:
            sliding_count = client.zcard(sliding_key)
        except Exception as err:  # noqa: BLE001
            print(f"  Failed to read {sliding_key}: {err}")

        try:
            global_val = client.get(global_key)
        except Exception as err:  # noqa: BLE001
            print(f"  Failed to read {global_key}: {err}")

        try:
            global_sliding_count = client.zcard(global_sliding_key)
        except Exception as err:  # noqa: BLE001
            print(f"  Failed to read {global_sliding_key}: {err}")
            global_sliding_count = None

        print(f"Model: {model}")
        print(f"  Cached usage ({usage_key}): {json.dumps(usage_val, indent=2) if usage_val is not None else 'None'}")
        print(f"  Sliding window entries ({sliding_key}): {sliding_count}")
        print(f"  Global usage ({global_key}): {json.dumps(global_val, indent=2) if global_val is not None else 'None'}")
        if global_sliding_count is not None:
            print(f"  Global sliding entries ({global_sliding_key}): {global_sliding_count}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect or reset Upstash rate limit usage.")
    parser.add_argument("ip", nargs="?", default="127.0.0.1", help="IP address to inspect/reset (default: 127.0.0.1)")
    parser.add_argument("--reset", action="store_true", help="Delete cached usage for the specified IP")
    parser.add_argument("--include-global", action="store_true", help="When resetting, also delete global backstop keys")

    args = parser.parse_args()

    if args.reset:
        reset_keys(args.ip, include_global=args.include_global)
    else:
        inspect(args.ip)


if __name__ == "__main__":
    main()
