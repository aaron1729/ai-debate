#!/usr/bin/env python3
"""
Retrospectively judge existing debates with multiple judges and turn counts.

This script allows you to:
1. Re-judge existing debates at different turn cutoffs (1 to T)
2. Use multiple different judge models
3. Analyze judge agreement and verdict stability over turns
"""

import argparse
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.core.experiment_store import SQLiteExperimentStore
from scripts.core.debate import Judge, MODELS

def estimate_cost(num_experiments: int, turns_per_experiment: int, num_judges: int) -> Dict[str, Any]:
    """
    Estimate the cost of running retrospective judging.

    Args:
        num_experiments: Number of experiments to judge
        turns_per_experiment: Average number of turn cutoffs per experiment
        num_judges: Number of different judge models

    Returns:
        Dictionary with cost estimates
    """
    # Each turn cutoff requires one judge call per judge model
    total_judgments = num_experiments * turns_per_experiment * num_judges

    # Rough cost estimates (in USD) - these are approximations
    cost_per_judgment = {
        "claude-sonnet-4-5-20250929": 0.015,  # Based on input/output tokens
        "gpt-4-turbo-preview": 0.010,
        "gemini-2.5-flash": 0.002,
        "grok-3": 0.010,
    }

    total_cost = 0
    for judge_id in MODELS.values():
        total_cost += cost_per_judgment.get(judge_id['id'], 0.01)

    avg_cost_per_judgment = total_cost / len(MODELS)
    estimated_total = total_judgments * avg_cost_per_judgment

    return {
        "total_judgments": total_judgments,
        "avg_cost_per_judgment": avg_cost_per_judgment,
        "estimated_total_cost": estimated_total,
        "breakdown": {
            "experiments": num_experiments,
            "turns_per_experiment": turns_per_experiment,
            "judges": num_judges
        }
    }


def truncate_debate_transcript(full_transcript: List[Dict[str, Any]], max_turns: int) -> List[Dict[str, Any]]:
    """
    Truncate a debate transcript to a specific number of turns.

    Args:
        full_transcript: Full debate transcript
        max_turns: Maximum number of turns to include

    Returns:
        Truncated transcript
    """
    # Filter by turn number (each turn has both pro and con arguments)
    return [entry for entry in full_transcript if entry.get("turn", 0) <= max_turns]


def judge_at_turn_cutoff(claim: str, transcript: List[Dict[str, Any]],
                         judge_model: str, turns: int) -> Optional[Dict[str, Any]]:
    """
    Judge a debate using only the first N turns.

    Args:
        claim: The claim being debated
        transcript: Full debate transcript
        judge_model: Model key for the judge
        turns: Number of turns to consider

    Returns:
        Judgment dictionary or None if error
    """
    # Truncate transcript
    truncated = truncate_debate_transcript(transcript, turns)

    if not truncated:
        print(f"  Warning: No transcript entries for turn {turns}", file=sys.stderr)
        return None

    # Convert transcript format to debate history format expected by Judge
    # Note: The stored transcript doesn't have 'context', so we use an empty string
    debate_history = []
    for entry in truncated:
        history_entry = {
            "position": entry.get("debater", ""),
            "url": entry.get("source_url", ""),
            "quote": entry.get("source_quote", ""),
            "context": "",  # Not stored in transcript, only used during debate
            "argument": entry.get("argument", ""),
            "refused": entry.get("refused", False)
        }
        if entry.get("refused"):
            history_entry["refusal_reason"] = entry.get("refusal_reason", "")
        debate_history.append(history_entry)

    # Create judge and get verdict
    try:
        judge = Judge(judge_model)
        verdict = judge.judge_debate(claim, debate_history)
        return verdict
    except Exception as e:
        print(f"  Error from judge {judge_model} at turn {turns}: {e}", file=sys.stderr)
        return None


def process_experiment(experiment_id: int, experiment_data: Dict[str, Any],
                       judge_models: List[str], turns_range: range,
                       store: SQLiteExperimentStore, skip_existing: bool = True) -> int:
    """
    Process a single experiment with multiple judges and turn cutoffs.

    Args:
        experiment_id: Experiment ID
        experiment_data: Experiment data from database
        judge_models: List of judge model keys
        turns_range: Range of turn cutoffs to evaluate
        store: Database store
        skip_existing: Whether to skip existing judgments

    Returns:
        Number of new judgments created
    """
    claim = experiment_data["claim_data"]["claim"]
    transcript = experiment_data["debate_transcript"]
    max_turns = experiment_data["experiment_config"]["turns"]

    print(f"\nExperiment {experiment_id}: {claim[:80]}...")
    print(f"  Max turns: {max_turns}")

    judgments_created = 0

    for turns in turns_range:
        if turns > max_turns:
            continue

        for judge_model in judge_models:
            judge_id = MODELS[judge_model]["id"]

            print(f"  Judging with {MODELS[judge_model]['name']} at turn {turns}...", end=" ")

            verdict = judge_at_turn_cutoff(claim, transcript, judge_model, turns)

            if verdict:
                # Save to database
                judgment_id = store.save_judgment(
                    experiment_id=experiment_id,
                    judge_model=judge_id,
                    turns_considered=turns,
                    verdict=verdict["verdict"],
                    score=verdict["score"],
                    reasoning=verdict["explanation"]
                )

                print(f"✓ (verdict: {verdict['verdict']}, score: {verdict['score']})")
                judgments_created += 1
            else:
                print("✗ (error)")

    return judgments_created


def main():
    parser = argparse.ArgumentParser(
        description="Retrospectively judge existing debates with multiple judges and turn counts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Judge all experiments with turns=6 using all 4 judges
  python judge_existing_debates.py --turns 6 --turns-range 1-6 --judges all

  # Judge specific experiments with only Claude and GPT-4
  python judge_existing_debates.py --experiment-ids 1,2,3 --judges claude,gpt4 --turns-range 1-4

  # Estimate cost before running
  python judge_existing_debates.py --turns 6 --judges all --estimate-only

Available judges: claude, gpt4, gemini, grok
        """
    )

    parser.add_argument(
        "--experiment-ids",
        type=str,
        help="Comma-separated experiment IDs or 'all' (default: all with specified turns)"
    )

    parser.add_argument(
        "--turns",
        type=int,
        help="Filter experiments by number of turns (e.g., 6)"
    )

    parser.add_argument(
        "--turns-range",
        type=str,
        default="1-6",
        help="Range of turn cutoffs to evaluate (e.g., '1-6' or '2-4'). Default: 1-6"
    )

    parser.add_argument(
        "--judges",
        type=str,
        default="all",
        help="Comma-separated list of judge models or 'all' (default: all)"
    )

    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip judgments that already exist (default: True)"
    )

    parser.add_argument(
        "--force-rejudge",
        action="store_true",
        help="Force re-judging even if judgments exist"
    )

    parser.add_argument(
        "--estimate-only",
        action="store_true",
        help="Only estimate cost without running"
    )

    args = parser.parse_args()

    # Parse judge models
    if args.judges == "all":
        judge_models = list(MODELS.keys())
    else:
        judge_models = [j.strip() for j in args.judges.split(",")]
        for j in judge_models:
            if j not in MODELS:
                print(f"Error: Unknown judge model '{j}'. Available: {list(MODELS.keys())}", file=sys.stderr)
                sys.exit(1)

    # Parse turns range
    try:
        if "-" in args.turns_range:
            start, end = args.turns_range.split("-")
            turns_range = range(int(start), int(end) + 1)
        else:
            turns_range = range(int(args.turns_range), int(args.turns_range) + 1)
    except ValueError:
        print(f"Error: Invalid turns range '{args.turns_range}'. Use format like '1-6' or '3'", file=sys.stderr)
        sys.exit(1)

    # Load experiments
    store = SQLiteExperimentStore()

    if args.experiment_ids == "all" or args.experiment_ids is None:
        # Get all experiments matching filter
        filters = {}
        if args.turns:
            # We need to query by turns, but query() doesn't support that
            # So we'll get all and filter
            all_experiments = store.get_all()
            experiments = [
                (i, exp) for i, exp in enumerate(all_experiments, 1)
                if exp["experiment_config"]["turns"] == args.turns
            ]
        else:
            all_experiments = store.get_all()
            experiments = list(enumerate(all_experiments, 1))
    else:
        # Parse specific IDs
        try:
            exp_ids = [int(x.strip()) for x in args.experiment_ids.split(",")]
            experiments = []
            for exp_id in exp_ids:
                exp_data = store.get_by_id(exp_id)
                if exp_data:
                    experiments.append((exp_id, exp_data))
                else:
                    print(f"Warning: Experiment {exp_id} not found", file=sys.stderr)
        except ValueError:
            print(f"Error: Invalid experiment IDs '{args.experiment_ids}'", file=sys.stderr)
            sys.exit(1)

    if not experiments:
        print("No experiments found matching criteria", file=sys.stderr)
        sys.exit(1)

    # Calculate average turns for cost estimate
    avg_turns = sum(len([t for t in turns_range if t <= exp[1]["experiment_config"]["turns"]])
                   for exp in experiments) / len(experiments)

    # Estimate cost
    cost_estimate = estimate_cost(len(experiments), int(avg_turns), len(judge_models))

    print(f"\n{'='*80}")
    print("RETROSPECTIVE JUDGING PLAN")
    print(f"{'='*80}\n")
    print(f"Experiments to process: {len(experiments)}")
    print(f"Judge models: {', '.join([MODELS[j]['name'] for j in judge_models])}")
    print(f"Turn range: {min(turns_range)}-{max(turns_range)}")
    print(f"\nEstimated judgments: {cost_estimate['total_judgments']}")
    print(f"Estimated cost: ${cost_estimate['estimated_total_cost']:.2f}")
    print(f"  (Avg ${cost_estimate['avg_cost_per_judgment']:.4f} per judgment)")
    print(f"\n{'='*80}\n")

    if args.estimate_only:
        print("Estimate only mode - exiting without judging")
        sys.exit(0)

    # Confirm before proceeding
    if cost_estimate['estimated_total_cost'] > 1.0:
        response = input(f"Proceed with ~${cost_estimate['estimated_total_cost']:.2f} in API costs? (yes/no): ")
        if response.lower() not in ["yes", "y"]:
            print("Cancelled by user")
            sys.exit(0)

    # Process experiments
    total_judgments = 0
    skip_existing = args.skip_existing and not args.force_rejudge

    for exp_id, exp_data in experiments:
        judgments_created = process_experiment(
            exp_id, exp_data, judge_models, turns_range, store, skip_existing
        )
        total_judgments += judgments_created

    print(f"\n{'='*80}")
    print(f"COMPLETED: Created {total_judgments} new judgments")
    print(f"{'='*80}\n")

    # Show summary statistics
    stats = store.get_judgment_stats()
    print("Judgment Statistics:")
    print(f"  Total judgments in database: {stats['total_judgments']}")
    print(f"  By judge model: {stats['by_judge_model']}")
    print(f"  By turns considered: {stats['by_turns']}")
    if stats.get('perfect_agreement_rate') is not None:
        print(f"  Perfect agreement rate: {stats['perfect_agreement_rate']:.1%}")


if __name__ == "__main__":
    main()
