#!/usr/bin/env python3
"""
Run a complete debate motion experiment suite.

This script runs the comprehensive experimental design for debate motions:
1. Runs 4 full debates (6 rounds each) with all position/order combinations
2. Has all 4 judge models evaluate each debate at turn lengths 1, 2, 4, 6
3. Total: 4 debates × 4 judges × 4 turn lengths = 64 judgments per motion

The 4 debate configurations are:
  Config 1: Debater1=pro, Debater2=con, pro goes first
  Config 2: Debater1=pro, Debater2=con, con goes first
  Config 3: Debater2=pro, Debater1=con, pro goes first
  Config 4: Debater2=pro, Debater1=con, con goes first

Usage examples:
  # Run full suite on motion 0 with Claude vs Grok
  python run_debate_motion_suite.py --motion 0 --debater1 claude --debater2 grok

  # Run with specific models
  python run_debate_motion_suite.py --motion 5 --debater1 gpt4 --debater2 gemini

  # Random motion, specified debaters
  python run_debate_motion_suite.py --debater1 claude --debater2 grok --seed 42
"""

import argparse
import json
import os
import random
import subprocess
import sys
from typing import List

from model_client import all_available_model_keys, get_model_name


def load_debate_motions(filepath: str = "data/debate_motions.json") -> list[dict]:
    """Load debate motions from JSON file."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Debate motions file not found: {filepath}")

    with open(filepath, 'r') as f:
        motions = json.load(f)

    if not isinstance(motions, list):
        raise ValueError(f"Debate motions file must contain a JSON array")

    if not motions:
        raise ValueError(f"No motions found in {filepath}")

    return motions


def run_debate_config(motion_idx: int, pro_model: str, con_model: str,
                     pro_first: bool, motions_file: str) -> int:
    """
    Run a single debate configuration.

    Args:
        motion_idx: Index of the motion
        pro_model: Model arguing pro side
        con_model: Model arguing con side
        pro_first: Whether pro goes first (if False, con goes first)
        motions_file: Path to motions file

    Returns:
        Experiment ID
    """
    cmd = [
        sys.executable,
        "run_single_debate.py",
        "--motion", str(motion_idx),
        "--debater1", pro_model,
        "--debater2", con_model,
        "--rounds", "6",
        "--motions-file", motions_file
    ]

    # Add --con-first flag if con goes first
    if not pro_first:
        cmd.append("--con-first")

    order = "pro_first" if pro_first else "con_first"
    print(f"\n{'='*80}")
    print(f"Running Config: {get_model_name(pro_model)}(pro) vs {get_model_name(con_model)}(con), {order}")
    print(f"{'='*80}\n")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error running debate:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"Debate failed with exit code {result.returncode}")

    # Extract experiment ID from output
    output = result.stdout
    for line in output.split('\n'):
        if 'Experiment saved to database (ID:' in line:
            # Extract ID from line like "Experiment saved to database (ID: 123)"
            exp_id = int(line.split('(ID:')[1].strip().rstrip(')'))
            return exp_id

    raise RuntimeError("Could not find experiment ID in debate output")


def run_judging(experiment_ids: List[int]) -> None:
    """
    Run judging on all experiment IDs with all judges and turn ranges.

    Args:
        experiment_ids: List of experiment IDs to judge
    """
    cmd = [
        sys.executable,
        "judge_existing_debates.py",
        "--experiment-ids", ",".join(map(str, experiment_ids)),
        "--judges", "all",
        "--turns-range", "1-6"
    ]

    print(f"\n{'='*80}")
    print(f"Running Judgments: 4 judges × 4 turn lengths × {len(experiment_ids)} debates")
    print(f"{'='*80}\n")

    # Use 'yes' to auto-confirm the judgment process
    yes_process = subprocess.Popen(['echo', 'yes'], stdout=subprocess.PIPE)
    result = subprocess.run(cmd, stdin=yes_process.stdout, capture_output=True, text=True)
    yes_process.wait()

    if result.returncode != 0:
        print(f"Error running judgments:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"Judging failed with exit code {result.returncode}")

    print(result.stdout)


def main():
    parser = argparse.ArgumentParser(
        description="Run complete debate motion experiment suite (4 debates + 64 judgments)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available models: {', '.join(all_available_model_keys())}

Experiment Design:
  4 debate configurations (all 6 rounds):
    1. Debater1=pro, Debater2=con, pro first
    2. Debater1=pro, Debater2=con, con first
    3. Debater2=pro, Debater1=con, pro first
    4. Debater2=pro, Debater1=con, con first

  64 judgments total:
    - 4 judges: {', '.join(all_available_model_keys())}
    - 4 turn lengths: 1, 2, 4, 6
    - 4 debates

This captures:
  - Position effect (pro vs con)
  - Order effect (first vs second)
  - Judge agreement
  - Progressive evaluation

Examples:
  python run_debate_motion_suite.py --motion 0 --debater1 claude --debater2 grok
  python run_debate_motion_suite.py --motion 5 --debater1 gpt4 --debater2 gemini
  python run_debate_motion_suite.py --debater1 claude --debater2 grok --seed 42
"""
    )

    parser.add_argument(
        "--motion",
        type=int,
        help="Index of the motion in debate_motions.json (if not specified, chosen randomly)"
    )

    parser.add_argument(
        "--debater1",
        type=str,
        required=True,
        choices=list(all_available_model_keys()),
        help="First debater model"
    )

    parser.add_argument(
        "--debater2",
        type=str,
        required=True,
        choices=list(all_available_model_keys()),
        help="Second debater model (must be different from debater1)"
    )

    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducible random motion selection"
    )

    parser.add_argument(
        "--motions-file",
        type=str,
        default="data/debate_motions.json",
        help="Path to debate motions JSON file (default: data/debate_motions.json)"
    )

    parser.add_argument(
        "--debates-only",
        action="store_true",
        help="Only run the debates, skip judging (useful for testing)"
    )

    args = parser.parse_args()

    # Validate debaters are different
    if args.debater1 == args.debater2:
        print("Error: debater1 and debater2 must be different models", file=sys.stderr)
        sys.exit(1)

    # Set random seed if provided
    if args.seed is not None:
        random.seed(args.seed)
        print(f"Using random seed: {args.seed}")

    try:
        # Load motions
        motions = load_debate_motions(args.motions_file)

        # Select motion
        if args.motion is not None:
            if args.motion < 0 or args.motion >= len(motions):
                print(f"Error: Motion index {args.motion} out of range (0-{len(motions)-1})", file=sys.stderr)
                sys.exit(1)
            motion_idx = args.motion
            print(f"Using specified motion index: {motion_idx}")
        else:
            motion_idx = random.randint(0, len(motions) - 1)
            print(f"Randomly selected motion index: {motion_idx}")

        motion_data = motions[motion_idx]
        motion_text = motion_data.get("motion")

        print("\n" + "=" * 80)
        print("DEBATE MOTION EXPERIMENT SUITE")
        print("=" * 80)
        print(f"Motion: {motion_text}")
        print(f"Debater 1: {get_model_name(args.debater1)}")
        print(f"Debater 2: {get_model_name(args.debater2)}")
        print(f"\nRunning 4 debate configurations...")
        print("=" * 80)

        # Run all 4 debate configurations
        experiment_ids = []

        # Config 1: Debater1=pro, Debater2=con, pro first
        exp_id = run_debate_config(motion_idx, args.debater1, args.debater2, True, args.motions_file)
        experiment_ids.append(exp_id)
        print(f"✓ Config 1 complete (Experiment ID: {exp_id})")

        # Config 2: Debater1=pro, Debater2=con, con first
        exp_id = run_debate_config(motion_idx, args.debater1, args.debater2, False, args.motions_file)
        experiment_ids.append(exp_id)
        print(f"✓ Config 2 complete (Experiment ID: {exp_id})")

        # Config 3: Debater2=pro, Debater1=con, pro first
        exp_id = run_debate_config(motion_idx, args.debater2, args.debater1, True, args.motions_file)
        experiment_ids.append(exp_id)
        print(f"✓ Config 3 complete (Experiment ID: {exp_id})")

        # Config 4: Debater2=pro, Debater1=con, con first
        exp_id = run_debate_config(motion_idx, args.debater2, args.debater1, False, args.motions_file)
        experiment_ids.append(exp_id)
        print(f"✓ Config 4 complete (Experiment ID: {exp_id})")

        print("\n" + "=" * 80)
        print("ALL DEBATES COMPLETE")
        print("=" * 80)
        print(f"Experiment IDs: {', '.join(map(str, experiment_ids))}")

        if args.debates_only:
            print("\n--debates-only flag set, skipping judgments")
            print(f"\nTo judge these debates later, run:")
            print(f"  python judge_existing_debates.py --experiment-ids {','.join(map(str, experiment_ids))} --judges all --turns-range 1-6")
        else:
            # Run judging
            run_judging(experiment_ids)

            print("\n" + "=" * 80)
            print("EXPERIMENT SUITE COMPLETE")
            print("=" * 80)
            print(f"Total judgments: 64 (4 debates × 4 judges × 4 turn lengths)")
            print(f"\nTo query results:")
            print(f"  python query_experiments.py")

    except KeyboardInterrupt:
        print("\n\nExperiment suite interrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
