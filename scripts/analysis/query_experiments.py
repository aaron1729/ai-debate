#!/usr/bin/env python3
"""
Query and analyze debate experiments from SQLite database.
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.core.experiment_store import SQLiteExperimentStore


def format_experiment_summary(exp: dict, verbose: bool = False) -> str:
    """Format an experiment for display."""
    exp_id = exp.get("id", "?")
    claim_data = exp.get("claim_data", {})
    config = exp.get("experiment_config", {})
    judge = exp.get("judge_decision", {})
    ground_truth = exp.get("ground_truth", {})

    claim = claim_data.get("claim", "")[:80]
    if len(claim_data.get("claim", "")) > 80:
        claim += "..."

    output = f"[ID {exp_id}] {claim}\n"
    output += f"  Topic: {claim_data.get('topic', 'N/A')}\n"
    output += f"  Judge: {judge.get('verdict', 'N/A')} (score: {judge.get('score', '?')})\n"

    if ground_truth.get("verdict"):
        output += f"  Ground Truth: {ground_truth['verdict']}"
        match = "✓" if judge.get("verdict") == ground_truth["verdict"] else "✗"
        output += f" {match}\n"

    if verbose:
        models = config.get("models", {})
        output += f"  Models: Pro={models.get('pro', '?')}, Con={models.get('con', '?')}, Judge={models.get('judge', '?')}\n"
        output += f"  Turns: {config.get('turns', '?')}, Pro first: {config.get('pro_went_first', '?')}\n"
        output += f"  Timestamp: {config.get('timestamp', 'N/A')}\n"

    return output


def main():
    parser = argparse.ArgumentParser(
        description="Query and analyze debate experiments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python query_experiments.py --list
  python query_experiments.py --stats
  python query_experiments.py --topic climate --min-score 7
  python query_experiments.py --judge-verdict supported
  python query_experiments.py --export results.json --topic health
  python query_experiments.py --get 5
        """
    )

    # Actions
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument(
        "--list",
        action="store_true",
        help="List all experiments (default action)"
    )
    action_group.add_argument(
        "--stats",
        action="store_true",
        help="Show aggregate statistics"
    )
    action_group.add_argument(
        "--get",
        type=int,
        metavar="ID",
        help="Get a specific experiment by ID"
    )

    # Filters
    parser.add_argument(
        "--topic",
        type=str,
        help="Filter by topic"
    )
    parser.add_argument(
        "--judge-verdict",
        type=str,
        choices=["supported", "contradicted", "misleading", "needs more evidence"],
        help="Filter by judge verdict"
    )
    parser.add_argument(
        "--gt-verdict",
        type=str,
        choices=["supported", "contradicted", "misleading", "needs more evidence"],
        help="Filter by ground truth verdict"
    )
    parser.add_argument(
        "--min-score",
        type=int,
        help="Minimum judge score (-1 to 10)"
    )
    parser.add_argument(
        "--max-score",
        type=int,
        help="Maximum judge score (-1 to 10)"
    )
    parser.add_argument(
        "--pro-model",
        type=str,
        help="Filter by pro model"
    )
    parser.add_argument(
        "--con-model",
        type=str,
        help="Filter by con model"
    )
    parser.add_argument(
        "--judge-model",
        type=str,
        help="Filter by judge model"
    )

    # Output options
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed information"
    )
    parser.add_argument(
        "--export",
        type=str,
        metavar="FILE",
        help="Export results to JSON file"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Limit number of results (default: 50)"
    )

    args = parser.parse_args()

    # Initialize store
    store = SQLiteExperimentStore()

    # Handle --get
    if args.get:
        experiment = store.get_by_id(args.get)
        if not experiment:
            print(f"Experiment {args.get} not found", file=sys.stderr)
            sys.exit(1)

        if args.export:
            with open(args.export, 'w') as f:
                json.dump(experiment, f, indent=2)
            print(f"Exported experiment {args.get} to {args.export}")
        else:
            print(json.dumps(experiment, indent=2))
        return

    # Handle --stats
    if args.stats:
        stats = store.get_stats()
        print("=== Experiment Statistics ===\n")
        print(f"Total experiments: {stats['total_experiments']}")
        print(f"\nBy verdict:")
        for verdict, count in stats.get('by_verdict', {}).items():
            print(f"  {verdict}: {count}")
        print(f"\nBy topic:")
        for topic, count in stats.get('by_topic', {}).items():
            print(f"  {topic}: {count}")
        if stats.get('average_score') is not None:
            print(f"\nAverage score: {stats['average_score']}")
        print(f"\nScore distribution:")
        for category, count in stats.get('score_distribution', {}).items():
            print(f"  {category}: {count}")
        return

    # Build filters
    filters = {}
    if args.topic:
        filters["topic"] = args.topic
    if args.judge_verdict:
        filters["judge_verdict"] = args.judge_verdict
    if args.gt_verdict:
        filters["gt_verdict"] = args.gt_verdict
    if args.min_score is not None:
        filters["min_score"] = args.min_score
    if args.max_score is not None:
        filters["max_score"] = args.max_score
    if args.pro_model:
        filters["pro_model"] = args.pro_model
    if args.con_model:
        filters["con_model"] = args.con_model
    if args.judge_model:
        filters["judge_model"] = args.judge_model

    # Query experiments
    experiments = store.query(filters)

    if not experiments:
        print("No experiments found matching criteria")
        return

    # Apply limit
    if args.limit and len(experiments) > args.limit:
        print(f"Showing first {args.limit} of {len(experiments)} experiments\n")
        experiments = experiments[:args.limit]

    # Export if requested
    if args.export:
        with open(args.export, 'w') as f:
            json.dump(experiments, f, indent=2)
        print(f"Exported {len(experiments)} experiments to {args.export}")
        return

    # List experiments
    print(f"Found {len(experiments)} experiments:\n")
    for i, exp in enumerate(experiments, 1):
        # Add ID to experiment dict for display
        # (it's in the full_data but not at top level)
        config = exp.get("experiment_config", {})
        timestamp = config.get("timestamp", "")
        exp["id"] = i if not timestamp else timestamp.split("T")[0]  # Use date as pseudo-ID for display

        print(format_experiment_summary(exp, verbose=args.verbose))
        print()


if __name__ == "__main__":
    main()
