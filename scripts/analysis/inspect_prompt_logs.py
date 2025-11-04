#!/usr/bin/env python3
"""
Utility script for inspecting debate prompt logs stored in Upstash Redis.

Usage examples:

    python inspect_prompt_logs.py list --limit 5 --summary
    python inspect_prompt_logs.py get promptlog:2025-01-12T21:48:33.512Z:abc123 --summary
    python inspect_prompt_logs.py stats

The script loads `.env` (if present) so you can reuse the same credentials you
use for local development:
  - UPSTASH_REDIS_REST_URL
  - UPSTASH_REDIS_REST_TOKEN

NOTE: The prompt logging feature itself is newly added and not fully validated.
Treat these results as diagnostic until you have confirmed them in your own
environment.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, Iterable, List, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

PROMPT_LOG_INDEX_KEY = 'promptlog:index'
PROMPT_LOG_SIZE_HASH = 'promptlog:sizes'
PROMPT_LOG_TOTAL_BYTES_KEY = 'promptlog:total_bytes'

DEFAULT_SUMMARY_FIELDS: Sequence[str] = (
    'metadata.createdAt',
    'metadata.claim',
    'metadata.turns',
    'metadata.proModel',
    'metadata.conModel',
    'metadata.judgeModel',
    'metadata.firstSpeaker',
    'metadata.usingServerKeys',
    'metadata.userApiKeyProviders',
    'metadata.ipHash',
    'metadata.userAgent',
)


def load_env_file(path: str = '.env') -> None:
  """Load key=value pairs from a .env file if present."""
  if not os.path.exists(path):
    return
  try:
    with open(path, 'r', encoding='utf-8') as env_file:
      for line in env_file:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
          continue
        if '=' not in stripped:
          continue
        key, value = stripped.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
          os.environ[key] = value
  except OSError as err:
    raise RuntimeError(f'Failed to read {path}: {err}') from err


def require_env(name: str) -> str:
  value = os.environ.get(name)
  if not value:
    raise RuntimeError(f'Environment variable {name} is required for this script.')
  return value


def api_request(path: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
  base_url = require_env('UPSTASH_REDIS_REST_URL').rstrip('/')
  token = require_env('UPSTASH_REDIS_REST_TOKEN')

  url = f'{base_url}/{path.lstrip("/")}'
  if params:
    url = f'{url}?{urlencode(params)}'

  req = Request(url, headers={'Authorization': f'Bearer {token}'})
  try:
    with urlopen(req, timeout=15) as resp:
      payload = resp.read().decode('utf-8')
  except HTTPError as err:
    body = err.read().decode('utf-8', errors='replace')
    raise RuntimeError(f'Upstash request failed ({err.code}): {body}') from err
  except URLError as err:
    raise RuntimeError(f'Failed to reach Upstash: {err}') from err

  try:
    return json.loads(payload)
  except json.JSONDecodeError as err:
    raise RuntimeError(f'Invalid JSON in Upstash response: {payload}') from err


def list_logs(limit: int) -> List[str]:
  path = f'zrevrange/{quote(PROMPT_LOG_INDEX_KEY, safe="")}/0/{max(limit - 1, 0)}'
  data = api_request(path)
  result = data.get('result') or []
  return [str(member) for member in result]


def get_log(key: str) -> Dict[str, Any] | None:
  path = f'get/{quote(key, safe="")}'
  data = api_request(path)
  result = data.get('result')
  if result is None:
    return None
  if isinstance(result, str):
    try:
      return json.loads(result)
    except json.JSONDecodeError:
      return None
  if isinstance(result, dict):
    return result
  return None


def get_size(key: str) -> int | None:
  path = f'hget/{quote(PROMPT_LOG_SIZE_HASH, safe="")}/{quote(key, safe="")}'
  data = api_request(path)
  result = data.get('result')
  if result is None:
    return None
  try:
    return int(result)
  except (TypeError, ValueError):
    return None


def get_score(key: str) -> float | None:
  path = f'zscore/{quote(PROMPT_LOG_INDEX_KEY, safe="")}/{quote(key, safe="")}'
  data = api_request(path)
  result = data.get('result')
  if result is None:
    return None
  try:
    return float(result)
  except (TypeError, ValueError):
    return None


def get_total_bytes() -> int | None:
  path = f'get/{quote(PROMPT_LOG_TOTAL_BYTES_KEY, safe="")}'
  data = api_request(path)
  result = data.get('result')
  if result is None:
    return None
  try:
    return int(result)
  except (TypeError, ValueError):
    return None


def pluck_field(payload: Dict[str, Any], dotted: str) -> Any:
  parts = dotted.split('.')
  cursor: Any = payload
  for part in parts:
    if not isinstance(cursor, dict) or part not in cursor:
      return None
    cursor = cursor[part]
  return cursor


def format_summary(payload: Dict[str, Any], fields: Sequence[str]) -> Dict[str, Any]:
  return {field: pluck_field(payload, field) for field in fields}


def print_json(obj: Any) -> None:
  print(json.dumps(obj, indent=2, sort_keys=True))


def render_summary(summary: Dict[str, Any], as_json: bool) -> None:
  if as_json:
    print('    summary_json:')
    print_json(summary)
  else:
    print('    summary:')
    for key, value in summary.items():
      print(f'      {key}: {value}')


def cmd_list(args: argparse.Namespace) -> None:
  keys = list_logs(args.limit)
  if not keys:
    print('No prompt logs found.')
    return

  fields = DEFAULT_SUMMARY_FIELDS if args.summary_fields is None else args.summary_fields

  for idx, key in enumerate(keys, start=1):
    score = get_score(key) if args.include_scores else None
    prefix = f'{idx:>2}. {key}'
    if score is not None:
      prefix += f' (score={score})'
    print(prefix)

    payload: Dict[str, Any] | None = None
    if args.summary or args.include_payloads:
      payload = get_log(key)
      if payload is None:
        print('    payload: <missing>')
      else:
        if args.summary:
          summary = format_summary(payload, fields)
          render_summary(summary, args.summary_json)
        if args.include_payloads:
          print('    payload:')
          print_json(payload)

    if args.include_sizes:
      size = get_size(key)
      print(f'    approx_size_bytes: {size if size is not None else "unknown"}')


def cmd_get(args: argparse.Namespace) -> None:
  payload = get_log(args.key)
  if payload is None:
    print('Log entry not found.')
    return

  if args.include_size:
    size = get_size(args.key)
    print(f'# approx_size_bytes: {size if size is not None else "unknown"}')

  if args.summary:
    fields = args.summary_fields or DEFAULT_SUMMARY_FIELDS
    summary = format_summary(payload, fields)
    print_json(summary)
  else:
    print_json(payload)


def cmd_stats(_: argparse.Namespace) -> None:
  total_bytes = get_total_bytes()
  recent = list_logs(limit=1)
  newest = recent[0] if recent else 'none'
  print('Prompt log stats (best effort):')
  print(f'  total_bytes_tracked: {total_bytes if total_bytes is not None else "unknown"}')
  print(f'  newest_entry: {newest}')
  if recent:
    score = get_score(recent[0])
    if score is not None:
      print(f'  newest_entry_score: {score}')


def build_parser() -> argparse.ArgumentParser:
  parser = argparse.ArgumentParser(description='Inspect prompt logs stored in Upstash Redis.')
  sub = parser.add_subparsers(dest='command', required=True)

  list_parser = sub.add_parser('list', help='List recent prompt log keys.')
  list_parser.add_argument('--limit', type=int, default=5, help='Number of entries to list (default: 5).')
  list_parser.add_argument('--include-scores', action='store_true', help='Fetch and display sorted-set scores for each entry.')
  list_parser.add_argument('--include-payloads', action='store_true', help='Fetch and print payload JSON for each entry.')
  list_parser.add_argument('--include-sizes', action='store_true', help='Fetch recorded byte size for each entry.')
  list_parser.add_argument('--summary', action='store_true', help='Print a concise metadata summary for each entry.')
  list_parser.add_argument('--summary-json', action='store_true', help='When used with --summary, emit JSON instead of key/value lines.')
  list_parser.add_argument('--summary-fields', nargs='+', help='Override which dotted fields to include in summaries.')
  list_parser.set_defaults(func=cmd_list)

  get_parser = sub.add_parser('get', help='Fetch a specific prompt log payload by key.')
  get_parser.add_argument('key', help='Full Redis key, e.g. promptlog:2025-01-12T21:48:33.512Z:uuid')
  get_parser.add_argument('--include-size', action='store_true', help='Fetch recorded byte size for this entry.')
  get_parser.add_argument('--summary', action='store_true', help='Print only claim/metadata fields (default set).')
  get_parser.add_argument('--summary-fields', nargs='+', help='Override which dotted fields to include when using --summary.')
  get_parser.set_defaults(func=cmd_get)

  stats_parser = sub.add_parser('stats', help='Show aggregate statistics about prompt logs.')
  stats_parser.set_defaults(func=cmd_stats)

  return parser


def main(argv: Iterable[str]) -> int:
  load_env_file()
  parser = build_parser()
  args = parser.parse_args(list(argv))

  try:
    args.func(args)
  except RuntimeError as err:
    print(f'Error: {err}', file=sys.stderr)
    return 1
  except KeyboardInterrupt:
    print('Aborted.', file=sys.stderr)
    return 1

  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
