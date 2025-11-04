#!/usr/bin/env python3
"""
Run a single debate on a debate motion without a judge.

This script runs debates on real-world debate motions from debate_motions.json.
Unlike run_experiments.py (which runs systematic experiment suites with judges),
this script:
- Runs a single debate with a specified number of rounds (default: 6)
- Does NOT require a judge (debates are judged later via judge_existing_debates.py)
- Allows random selection of debaters WITH REPLACEMENT (same model can debate itself)
- Allows random selection of motion if not specified

Usage examples:
  # Random motion, random debaters, 6 rounds
  python run_single_debate.py

  # Specific motion (by index), random debaters
  python run_single_debate.py --motion 0

  # Specific debaters, random motion
  python run_single_debate.py --debater1 claude --debater2 grok

  # Specific motion and debaters, custom rounds
  python run_single_debate.py --motion 5 --debater1 gpt4 --debater2 gemini --rounds 4

  # Random with seed for reproducibility
  python run_single_debate.py --seed 42
"""

import argparse
import json
import os
import random
import sys
from typing import Optional

from debate import run_debate_no_judge
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


def select_random_debaters() -> tuple[str, str]:
    """
    Select two debaters randomly WITH REPLACEMENT.

    This means the same model can be selected for both sides,
    allowing models to debate themselves.

    Returns:
        Tuple of (debater1_key, debater2_key)
    """
    model_keys = list(all_available_model_keys())
    debater1 = random.choice(model_keys)
    debater2 = random.choice(model_keys)
    return debater1, debater2


def main():
    parser = argparse.ArgumentParser(
        description="Run a single debate on a debate motion without a judge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available models: {', '.join(all_available_model_keys())}

This script runs debates without immediate judging. Later, you can use
judge_existing_debates.py to have multiple judges assess the debates.

Examples:
  # Let the system choose everything randomly
  python run_single_debate.py

  # Specific debaters, random motion
  python run_single_debate.py --debater1 claude --debater2 grok

  # Random debaters, specific motion
  python run_single_debate.py --motion 0

  # Fully specified
  python run_single_debate.py --motion 5 --debater1 gpt4 --debater2 gemini --rounds 4
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
        choices=list(all_available_model_keys()),
        help="First debater model (if not specified, chosen randomly)"
    )

    parser.add_argument(
        "--debater2",
        type=str,
        choices=list(all_available_model_keys()),
        help="Second debater model (if not specified, chosen randomly)"
    )

    parser.add_argument(
        "--rounds",
        type=int,
        default=6,
        choices=[1, 2, 3, 4, 5, 6],
        help="Number of rounds (turns per side) (default: 6)"
    )

    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducible random selections"
    )

    parser.add_argument(
        "--motions-file",
        type=str,
        default="data/debate_motions.json",
        help="Path to debate motions JSON file (default: data/debate_motions.json)"
    )

    parser.add_argument(
        "--con-first",
        action="store_true",
        help="Con debater goes first (default: pro goes first)"
    )

    args = parser.parse_args()

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
        topic = motion_data.get("topic")

        if not motion_text:
            print(f"Error: Motion at index {motion_idx} has no 'motion' field", file=sys.stderr)
            sys.exit(1)

        # Select debaters
        if args.debater1 and args.debater2:
            debater1 = args.debater1
            debater2 = args.debater2
            print(f"Using specified debaters: {get_model_name(debater1)} vs {get_model_name(debater2)}")
        elif args.debater1:
            debater1 = args.debater1
            debater2 = random.choice(list(all_available_model_keys()))
            print(f"Using debater1={get_model_name(debater1)}, randomly selected debater2={get_model_name(debater2)}")
        elif args.debater2:
            debater1 = random.choice(list(all_available_model_keys()))
            debater2 = args.debater2
            print(f"Randomly selected debater1={get_model_name(debater1)}, using debater2={get_model_name(debater2)}")
        else:
            debater1, debater2 = select_random_debaters()
            print(f"Randomly selected both debaters: {get_model_name(debater1)} vs {get_model_name(debater2)}")

        # Create claim_id for tracking
        claim_id = f"{args.motions_file}:{motion_idx}"

        # Display what we're about to do
        print("\n" + "=" * 80)
        print("DEBATE CONFIGURATION")
        print("=" * 80)
        print(f"Motion: {motion_text}")
        if topic:
            print(f"Topic: {topic}")
        print(f"Motion index: {motion_idx}")
        print(f"Pro debater: {get_model_name(debater1)}")
        print(f"Con debater: {get_model_name(debater2)}")
        print(f"Rounds: {args.rounds}")
        print(f"Going first: {'Con' if args.con_first else 'Pro'}")
        print(f"Judge: None (will be judged later)")
        print("=" * 80 + "\n")

        # Determine who goes first
        pro_went_first = not args.con_first

        # Run the debate without a judge
        experiment_id = run_debate_no_judge(
            claim=motion_text,
            turns=args.rounds,
            pro_model=debater1,
            con_model=debater2,
            pro_went_first=pro_went_first,
            topic=topic,
            claim_id=claim_id,
            gt_verdict=None,  # No ground truth for debate motions
            gt_source=motion_data.get("source"),
            gt_url=motion_data.get("sourceUrl")
        )

        print("\n" + "=" * 80)
        print("DEBATE COMPLETE")
        print("=" * 80)
        print(f"Experiment ID: {experiment_id}")
        print(f"\nTo judge this debate later, run:")
        print(f"  python judge_existing_debates.py --experiment-ids {experiment_id} --judges all")
        print("=" * 80 + "\n")

    except KeyboardInterrupt:
        print("\n\nDebate interrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
