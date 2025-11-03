#!/usr/bin/env python3
"""
Debate Podcast Processing Script
Converts CSV files from debate podcasts into standardized JSON format with topic assignment.
"""

import os
import sys
import csv
import json
import argparse
from typing import Optional
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Import ModelClient and topics utilities from existing scripts
from model_client import ModelClient, all_available_model_keys, get_model_name
from process_factcheck_claims import load_topics, save_topics


def parse_percentage(pct_str: str) -> Optional[float]:
    """Parse percentage string like '50%' or '50.0%' to float."""
    if not pct_str or pct_str == 'N/A':
        return None
    try:
        return float(pct_str.strip().rstrip('%'))
    except (ValueError, AttributeError):
        return None


def parse_date(date_str: str) -> Optional[str]:
    """Convert various date formats to ISO 8601 format."""
    if not date_str or date_str == 'N/A' or date_str == 'Unlabeled' or date_str == 'Various':
        return None

    # Try different date formats
    formats = [
        "%b %d, %Y",  # Sep 20, 2011
        "%Y",  # 2019
        "%b %Y",  # Sep 2025
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.isoformat() + 'Z'
        except ValueError:
            continue

    # If it's just a year, use January 1st
    try:
        year = int(date_str.strip())
        return f"{year}-01-01T00:00:00Z"
    except ValueError:
        pass

    return None


def parse_vote_swing(swing_str: str) -> Optional[float]:
    """Parse vote swing string like '+10%' or '-5%' to float."""
    if not swing_str or swing_str == 'N/A':
        return None
    try:
        # Remove % and any whitespace
        clean = swing_str.strip().rstrip('%').replace('+', '')
        return float(clean)
    except (ValueError, AttributeError):
        return None


def assign_topic_with_llm(motion: str, model: ModelClient, topics: list[str]) -> str:
    """Use LLM to assign a topic to a debate motion."""
    topics_str = ", ".join(f'"{t}"' for t in topics)

    system_prompt = f"""You are a topic classification assistant. Given a debate motion/resolution, assign it to the most appropriate topic from the existing list, or create a new broad topic if needed.

Current topics: [{topics_str}]

Guidelines:
- Prefer existing topics when possible
- Keep topics BROAD (e.g., "climate" not "climate policy")
- Topics should be lowercase, single words or short phrases
- Only create new topic if motion clearly doesn't fit any existing category

Return ONLY the topic name, nothing else."""

    user_prompt = f"""Assign a topic to this debate motion:

"{motion}"

Return only the topic name."""

    try:
        response = model.generate(system_prompt, user_prompt, max_tokens=50)
        topic = response.strip().lower().strip('"').strip("'")

        # Add to topics list if new
        if topic not in topics:
            topics.append(topic)
            print(f"  → New topic added: '{topic}'")

        return topic
    except Exception as e:
        print(f"  Warning: Error assigning topic: {e}", file=sys.stderr)
        return "general"


def process_munk_debates(csv_path: str, model: Optional[ModelClient], topics: list[str]) -> list[dict]:
    """Process Munk Debates CSV file."""
    motions = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            motion_text = row['Debatable Claim (Resolution)'].strip()
            if not motion_text:
                continue

            # Parse voting data
            pre_vote = row['Pre-Debate Vote (For/Against)'].strip()
            post_vote = row['Post-Debate Vote (For/Against)'].strip()

            # Parse pre/post votes
            pre_for = pre_against = post_for = post_against = None
            if pre_vote and pre_vote != 'N/A':
                parts = pre_vote.split('/')
                if len(parts) == 2:
                    pre_for = parse_percentage(parts[0].strip())
                    pre_against = parse_percentage(parts[1].strip())

            if post_vote and post_vote != 'N/A':
                parts = post_vote.split('/')
                if len(parts) == 2:
                    post_for = parse_percentage(parts[0].strip())
                    post_against = parse_percentage(parts[1].strip())

            motion = {
                "motion": motion_text,
                "date": parse_date(row.get('Year', '')),
                "source": "Munk Debates",
                "sourceUrl": None,  # Not provided in CSV
                "preVote": {"for": pre_for, "against": pre_against},
                "postVote": {"for": post_for, "against": post_against},
                "voteSwing": {"pro": parse_vote_swing(row.get('Vote Swing (Pro)', ''))},
                "winner": row.get('Winner (by Vote Swing)', '').strip(),
                "type": "debate_motion"
            }

            # Assign topic
            if model:
                motion["topic"] = assign_topic_with_llm(motion_text, model, topics)
            else:
                motion["topic"] = "general"

            motions.append(motion)

    return motions


def process_open_to_debate(csv_path: str, model: Optional[ModelClient], topics: list[str]) -> list[dict]:
    """Process Open To Debate CSV file."""
    motions = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            motion_text = row['Debatable Claim (Motion)'].strip()
            if not motion_text:
                continue

            # Skip if unlabeled
            status = row.get('Status', '').strip()
            if 'Unlabeled' in status or 'Confirmed Motion' in status:
                # Skip motions without voting data
                pre_for = parse_percentage(row.get('Pre-Vote % For', ''))
                if pre_for is None:
                    continue

            motion = {
                "motion": motion_text,
                "date": parse_date(row.get('Debate Date', '')),
                "source": "Open To Debate",
                "sourceUrl": None,
                "preVote": {
                    "for": parse_percentage(row.get('Pre-Vote % For', '')),
                    "against": parse_percentage(row.get('Pre-Vote % Against', ''))
                },
                "postVote": {
                    "for": parse_percentage(row.get('Post-Vote % For', '')),
                    "against": parse_percentage(row.get('Post-Vote % Against', ''))
                },
                "voteSwing": {"pro": parse_percentage(row.get('Vote Swing % (For)', ''))},
                "winner": row.get('Winner (By Largest Swing)', '').strip(),
                "type": "debate_motion"
            }

            # Assign topic
            if model:
                motion["topic"] = assign_topic_with_llm(motion_text, model, topics)
            else:
                motion["topic"] = "general"

            motions.append(motion)

    return motions


def process_soho_forum(csv_path: str, model: Optional[ModelClient], topics: list[str]) -> list[dict]:
    """Process Soho Forum Debates CSV file."""
    motions = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            motion_text = row['Debatable Claim (Resolution)'].strip()
            if not motion_text:
                continue

            # Parse voting data
            pre_vote = row['Pre-Debate Vote (For/Against)'].strip()
            post_vote = row['Post-Debate Vote (For/Against)'].strip()

            # Parse pre/post votes
            pre_for = pre_against = post_for = post_against = None
            if pre_vote and pre_vote != 'N/A':
                parts = pre_vote.split('/')
                if len(parts) == 2:
                    pre_for = parse_percentage(parts[0].strip())
                    pre_against = parse_percentage(parts[1].strip())

            if post_vote and post_vote != 'N/A':
                parts = post_vote.split('/')
                if len(parts) == 2:
                    post_for = parse_percentage(parts[0].strip())
                    post_against = parse_percentage(parts[1].strip())

            motion = {
                "motion": motion_text,
                "date": parse_date(row.get('Date', '')),
                "source": "Soho Forum",
                "sourceUrl": None,
                "preVote": {"for": pre_for, "against": pre_against},
                "postVote": {"for": post_for, "against": post_against},
                "voteSwing": {"pro": parse_vote_swing(row.get('Vote Swing (Pro)', ''))},
                "winner": row.get('Winner (by Vote Swing)', '').strip(),
                "type": "debate_motion"
            }

            # Assign topic
            if model:
                motion["topic"] = assign_topic_with_llm(motion_text, model, topics)
            else:
                motion["topic"] = "general"

            motions.append(motion)

    return motions


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Process debate podcast CSV files into standardized JSON format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  python process_debate_podcasts.py data/debate-podcasts/raw/ -o data/debate_motions.json
  python process_debate_podcasts.py data/debate-podcasts/raw/ -o data/debate_motions.json --model claude

Available models: {', '.join(all_available_model_keys())}

The script will:
1. Read all CSV files from the input directory
2. Convert them to standardized JSON format
3. Optionally assign topics using an LLM
4. Combine all motions into a single output file
        """
    )

    parser.add_argument(
        "input_dir",
        help="Directory containing CSV files (e.g., data/debate-podcasts/raw/)"
    )

    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Output JSON file for debate motions"
    )

    parser.add_argument(
        "--model",
        default=None,
        choices=list(all_available_model_keys()),
        help="Model to use for topic assignment (default: None, assigns 'general' to all)"
    )

    parser.add_argument(
        "--topics-file",
        default="topics.json",
        help="Topics file to use/update (default: topics.json)"
    )

    args = parser.parse_args()

    # Validate input directory exists
    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory '{args.input_dir}' not found", file=sys.stderr)
        sys.exit(1)

    # Load topics
    topics = load_topics(args.topics_file)
    print(f"Loaded {len(topics)} existing topics: {', '.join(topics)}\n")

    # Initialize model if specified
    model = None
    if args.model:
        print(f"Initializing {get_model_name(args.model)} for topic assignment...")
        try:
            model = ModelClient(args.model)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        print()

    # Process each CSV file
    all_motions = []

    csv_files = {
        'Munk-Debates.csv': process_munk_debates,
        'Open-To-Debate.csv': process_open_to_debate,
        'Soho-Forum-Debates.csv': process_soho_forum,
    }

    for filename, processor_func in csv_files.items():
        csv_path = os.path.join(args.input_dir, filename)
        if os.path.exists(csv_path):
            print(f"Processing {filename}...")
            motions = processor_func(csv_path, model, topics)
            print(f"  ✓ Processed {len(motions)} motions\n")
            all_motions.extend(motions)
        else:
            print(f"  ✗ Skipping {filename} (not found)\n")

    # Save output
    print(f"Saving {len(all_motions)} motions to {args.output}...")
    with open(args.output, 'w') as f:
        json.dump(all_motions, f, indent=2)

    # Save updated topics
    if model:
        save_topics(topics, args.topics_file)
        print(f"Updated topics saved to {args.topics_file}")

    # Summary
    print("\n" + "=" * 80)
    print("PROCESSING COMPLETE")
    print("=" * 80)
    print(f"\nTotal debate motions processed: {len(all_motions)}")

    # Breakdown by source
    sources = {}
    for motion in all_motions:
        source = motion['source']
        sources[source] = sources.get(source, 0) + 1

    print("\nBreakdown by source:")
    for source, count in sorted(sources.items()):
        print(f"  {source}: {count}")

    # Breakdown by topic
    if model:
        topics_count = {}
        for motion in all_motions:
            topic = motion['topic']
            topics_count[topic] = topics_count.get(topic, 0) + 1

        print(f"\nBreakdown by topic:")
        for topic, count in sorted(topics_count.items(), key=lambda x: -x[1]):
            print(f"  {topic}: {count}")

    print(f"\nOutput saved to: {args.output}")
    print()


if __name__ == "__main__":
    main()
