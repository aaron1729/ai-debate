#!/usr/bin/env python3
"""
Randomized experiment runner.

This script repeatedly invokes run_experiments.py on randomly selected
claims and model configurations to explore the experiment space.
"""

import argparse
import glob
import json
import os
import random
import subprocess
import sys
from typing import List, Sequence, Tuple

from debate import MODELS


def discover_claim_files() -> List[str]:
    """Return all eligible claims files for random selection."""
    patterns = ["claims_verified_*.json", "claims_gpt5_*.json"]
    files: List[str] = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))

    # Filter out modification or skipped tracking files
    eligible = [
        path for path in files
        if not (
            path.endswith(".modifications.json")
            or path.endswith(".skipped.json")
        )
    ]
    return sorted(set(eligible))


def load_claim_counts(paths: Sequence[str]) -> List[Tuple[str, int]]:
    """Return (path, count) tuples for claim files with at least one claim."""
    results: List[Tuple[str, int]] = []
    for path in paths:
        try:
            with open(path, "r") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Warning: skipping {path} ({exc})", file=sys.stderr)
            continue

        if not isinstance(data, list):
            print(f"Warning: {path} does not contain a JSON array; skipping.", file=sys.stderr)
            continue

        if not data:
            print(f"Warning: {path} has no claims; skipping.", file=sys.stderr)
            continue

        results.append((path, len(data)))

    return results


def choose_random_claim(datasets: Sequence[Tuple[str, int]]) -> Tuple[str, int]:
    """Choose a random (file, index) pair uniformly across all claims."""
    total_claims = sum(count for _, count in datasets)
    if total_claims == 0:
        raise ValueError("No claims available for selection.")

    selection = random.randrange(total_claims)
    for path, count in datasets:
        if selection < count:
            return path, selection
        selection -= count

    # Should never reach here
    raise RuntimeError("Failed to select a claim; check dataset counts.")


def choose_models() -> Tuple[str, str, str]:
    """Select distinct model keys for debater1, debater2, and judge."""
    model_keys = list(MODELS.keys())
    selected = random.sample(model_keys, 3)
    return selected[0], selected[1], selected[2]


def run_experiment_suite(
    script_path: str,
    claim_spec: str,
    debater1: str,
    debater2: str,
    judge: str,
) -> int:
    """Invoke run_experiments.py and return its exit code."""
    cmd = [
        sys.executable,
        script_path,
        claim_spec,
        "--debater1",
        debater1,
        "--debater2",
        debater2,
        "--judge",
        judge,
    ]

    print("\n" + "=" * 80)
    print(f"Running experiment suite:")
    print(f"  Claim   : {claim_spec}")
    print(f"  Debater1: {debater1}")
    print(f"  Debater2: {debater2}")
    print(f"  Judge   : {judge}")
    print("=" * 80 + "\n")

    result = subprocess.run(cmd)
    return result.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Randomly run multiple experiment suites.",
    )
    parser.add_argument(
        "-n",
        "--count",
        type=int,
        default=10,
        help="Number of randomized runs to execute (default: 10)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducible runs.",
    )
    parser.add_argument(
        "--experiments-script",
        default="run_experiments.py",
        help="Path to run_experiments.py (default: run_experiments.py)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    claim_files = discover_claim_files()
    if not claim_files:
        print("Error: No claims files found matching the expected patterns.", file=sys.stderr)
        return 1

    datasets = load_claim_counts(claim_files)
    if not datasets:
        print("Error: No usable claims found in the discovered files.", file=sys.stderr)
        return 1

    script_path = os.path.abspath(args.experiments_script)
    if not os.path.isfile(script_path):
        print(f"Error: run_experiments script not found at {script_path}", file=sys.stderr)
        return 1

    print(f"Discovered {len(datasets)} datasets with {sum(count for _, count in datasets)} total claims.")
    print(f"Running {args.count} randomized experiment suite(s)...")

    for run_index in range(1, args.count + 1):
        print(f"\n--- Randomized Run {run_index}/{args.count} ---")
        claim_path, claim_idx = choose_random_claim(datasets)
        claim_spec = f"{claim_path}:{claim_idx}"
        debater1, debater2, judge = choose_models()

        exit_code = run_experiment_suite(
            script_path,
            claim_spec,
            debater1,
            debater2,
            judge,
        )

        if exit_code != 0:
            print(f"\nExperiment suite failed with exit code {exit_code}. Aborting further runs.", file=sys.stderr)
            return exit_code

    print("\nAll randomized experiment suites completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
