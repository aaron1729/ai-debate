#!/usr/bin/env python3
"""
Run systematic debate experiments with varying turn counts and debater orderings.

This script runs the 2x8 experiment design documented in claude.md:
- 4 turn counts: T=1, 2, 4, 6
- 2 debater orderings: (debater1 pro, debater2 con) and (debater2 pro, debater1 con)
- Total: 8 experiments per claim

Usage examples:
  # Run all 8 experiments on a specific claim
  python run_experiments.py claims_gpt5_01.json:0 --debater1 claude --debater2 grok --judge gpt4

  # Run with different debaters
  python run_experiments.py claims_verified_health_50.json:5 --debater1 gpt4 --debater2 gemini --judge claude
"""

import argparse
import json
import os
import sys
from typing import Optional
from debate import run_debate, MODELS


def load_claim_from_file(claim_spec: str) -> tuple[str, Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Load a claim from a JSON file.

    Args:
        claim_spec: String in format "filename:index" (e.g., "claims_gpt5_01.json:0")

    Returns:
        Tuple of (claim_text, topic, claim_id, gt_verdict, gt_source, gt_url)
    """
    if ":" not in claim_spec:
        raise ValueError(f"Claim spec must be in format 'filename:index', got: {claim_spec}")

    filename, index_str = claim_spec.rsplit(":", 1)

    try:
        index = int(index_str)
    except ValueError:
        raise ValueError(f"Index must be an integer, got: {index_str}")

    if not os.path.exists(filename):
        raise FileNotFoundError(f"Claims file not found: {filename}")

    with open(filename, 'r') as f:
        claims = json.load(f)

    if not isinstance(claims, list):
        raise ValueError(f"Claims file must contain a JSON array, got: {type(claims)}")

    if index < 0 or index >= len(claims):
        raise ValueError(f"Index {index} out of range (file has {len(claims)} claims)")

    claim_data = claims[index]

    # Extract fields - support multiple formats
    if isinstance(claim_data, dict):
        claim_text = claim_data.get("claim") or claim_data.get("text") or claim_data.get("motion")
        topic = claim_data.get("topic")
        gt_verdict = claim_data.get("verdict")
        gt_url = claim_data.get("url")

        # Determine source based on file naming pattern
        # For files named "claims_gpt5_*.json", source is "gpt5"
        # For "claims_verified_*.json", source comes from "publisher" field
        # For other files, check for "source" or "publisher" field
        basename = os.path.basename(filename)
        if basename.startswith("claims_gpt5"):
            gt_source = "gpt5"
        elif "publisher" in claim_data:
            gt_source = claim_data["publisher"]
        else:
            gt_source = claim_data.get("source")
    else:
        # If it's just a string
        claim_text = str(claim_data)
        topic = None
        gt_verdict = None
        gt_source = None
        gt_url = None

    if not claim_text:
        raise ValueError(f"Could not extract claim text from index {index}")

    # Use the full claim_spec as the claim_id
    claim_id = claim_spec

    return claim_text, topic, claim_id, gt_verdict, gt_source, gt_url


def run_experiment_suite(claim_spec: str, debater1: str, debater2: str, judge: str) -> list[int]:
    """
    Run the complete 2x8 experiment suite for a single claim.

    Args:
        claim_spec: Claim specification in format "filename:index"
        debater1: Model key for first debater (e.g., "claude")
        debater2: Model key for second debater (e.g., "grok")
        judge: Model key for judge (e.g., "gpt4")

    Returns:
        List of experiment IDs saved to database
    """
    # Validate models
    for model_key, role in [(debater1, "debater1"), (debater2, "debater2"), (judge, "judge")]:
        if model_key not in MODELS:
            raise ValueError(f"Unknown model for {role}: {model_key}. Available: {list(MODELS.keys())}")

    # Load claim
    print(f"\nLoading claim: {claim_spec}")
    claim_text, topic, claim_id, gt_verdict, gt_source, gt_url = load_claim_from_file(claim_spec)

    print(f"\nClaim: {claim_text}")
    if topic:
        print(f"Topic: {topic}")
    if gt_verdict:
        print(f"Ground truth: {gt_verdict}")
    print(f"\nDebaters: {MODELS[debater1]['name']} vs {MODELS[debater2]['name']}")
    print(f"Judge: {MODELS[judge]['name']}")
    print("\nRunning 8 experiments (4 turn counts × 2 orderings)...")
    print("=" * 80)

    experiment_ids = []
    turn_counts = [1, 2, 4, 6]

    # Configuration 1: debater1 pro, debater2 con (debater1 goes first)
    print(f"\nConfiguration 1: {MODELS[debater1]['name']} argues PRO, {MODELS[debater2]['name']} argues CON")
    print("-" * 80)
    for turns in turn_counts:
        print(f"\n>>> Running with T={turns} turns per side...")
        exp_id = run_debate(
            claim=claim_text,
            turns=turns,
            pro_model=debater1,
            con_model=debater2,
            judge_model=judge,
            pro_went_first=True,
            topic=topic,
            claim_id=claim_id,
            gt_verdict=gt_verdict,
            gt_source=gt_source,
            gt_url=gt_url
        )
        experiment_ids.append(exp_id)
        print(f"✓ Completed T={turns} (Experiment ID: {exp_id})")

    # Configuration 2: debater2 pro, debater1 con (debater2 goes first)
    print(f"\n\nConfiguration 2: {MODELS[debater2]['name']} argues PRO, {MODELS[debater1]['name']} argues CON")
    print("-" * 80)
    for turns in turn_counts:
        print(f"\n>>> Running with T={turns} turns per side...")
        exp_id = run_debate(
            claim=claim_text,
            turns=turns,
            pro_model=debater2,
            con_model=debater1,
            judge_model=judge,
            pro_went_first=True,
            topic=topic,
            claim_id=claim_id,
            gt_verdict=gt_verdict,
            gt_source=gt_source,
            gt_url=gt_url
        )
        experiment_ids.append(exp_id)
        print(f"✓ Completed T={turns} (Experiment ID: {exp_id})")

    return experiment_ids


def main():
    parser = argparse.ArgumentParser(
        description="Run systematic debate experiments with varying turn counts and debater orderings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available models: {', '.join(MODELS.keys())}

Experiment Design (2x8):
  - Turn counts: T=1, 2, 4, 6 (4 variations)
  - Orderings: 2 (debaters switch sides after first 4 experiments)
  - Total: 8 experiments per claim

Examples:
  # Claude vs Grok, judged by GPT-4
  python run_experiments.py data/claims_gpt5_01.json:0 --debater1 claude --debater2 grok --judge gpt4

  # GPT-4 vs Gemini, judged by Claude
  python run_experiments.py data/claims_verified_health_50.json:5 --debater1 gpt4 --debater2 gemini --judge claude

  # Test homeopathy claim (as documented in claude.md)
  python run_experiments.py data/claims_gpt5_01.json:1 --debater1 claude --debater2 grok --judge gpt4
"""
    )

    parser.add_argument(
        "claim",
        type=str,
        help='Claim specification in format "filename:index" (e.g., "claims_gpt5_01.json:0")'
    )

    parser.add_argument(
        "--debater1",
        type=str,
        required=True,
        choices=list(MODELS.keys()),
        help="First debater model (will argue PRO in first 4 experiments, CON in last 4)"
    )

    parser.add_argument(
        "--debater2",
        type=str,
        required=True,
        choices=list(MODELS.keys()),
        help="Second debater model (will argue CON in first 4 experiments, PRO in last 4)"
    )

    parser.add_argument(
        "--judge",
        type=str,
        required=True,
        choices=list(MODELS.keys()),
        help="Judge model (same for all 8 experiments)"
    )

    args = parser.parse_args()

    try:
        experiment_ids = run_experiment_suite(
            args.claim,
            args.debater1,
            args.debater2,
            args.judge
        )

        print("\n" + "=" * 80)
        print("EXPERIMENT SUITE COMPLETE")
        print("=" * 80)
        print(f"\nCompleted 8 experiments for claim: {args.claim}")
        print(f"Experiment IDs: {', '.join(map(str, experiment_ids))}")
        print(f"\nResults saved to experiments.db")
        print(f"\nTo query results, use:")
        print(f"  python query_experiments.py")

    except KeyboardInterrupt:
        print("\n\nExperiment suite interrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
