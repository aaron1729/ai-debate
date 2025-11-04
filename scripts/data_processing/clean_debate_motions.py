#!/usr/bin/env python3
"""
Clean Debate Motions Script
Rewrites debate motions to be standalone and unambiguous using an LLM.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.core.debate import ModelClient, MODELS


def get_system_prompt() -> str:
    """Generate the system prompt for motion cleaning."""
    return """You are a debate motion editor. Your task is to rewrite debate motions to be standalone and unambiguous while preserving their original meaning and intent.

## GUIDELINES FOR STANDALONE MOTIONS:

1. **Add temporal context for ALL motions**: Every debate happened at a specific time and reflected concerns of that era
   - For past debates (before ~2024): Use past tense with temporal framing
   - For recent debates (2024-2025): Use present tense with "As of [year]" framing
   - Even "timeless" claims should indicate WHEN they were being debated

   Examples:
   - "Men are obsolete" (2013) → "In the context of 2013, men were obsolete."
   - "Tax the rich more" (2013) → "As of 2013, governments should tax the rich more."
   - "Donald Trump can make America great again" (2016) → "In 2016, Donald Trump could make America great again."
   - "The West has lost the Middle East" (2014) → "As of 2014, the West had lost the Middle East."

2. **Use correct verb tenses**:
   - Past debates about past/completed events: Use past perfect ("had lost", "had been")
   - Past debates about then-present states: Use past tense ("were", "was")
   - Past debates about then-future possibilities: Use conditional past ("could", "would")
   - Recent debates about present: Use present tense with "As of [year]"

3. **Always end with proper punctuation**:
   - Every motion must be a complete sentence ending with a period
   - Remove trailing commas or incomplete phrasing

4. **Clarify ambiguous references**:
   - Replace "we" with the specific entity (e.g., "the United States", "Western nations")
   - Replace "the government" with the specific government when context is clear
   - Replace "this country" with the actual country name

5. **Convert questions to statements**:
   - "Do we need a Grand Strategy on China?" → "The United States needs a Grand Strategy on China."
   - "Will the Future Be Abundant?" → "The future will be abundant."
   - "Is War Inevitable?" → "War is inevitable."

6. **Preserve debate-ability**:
   - Keep the motion debatable (someone can argue for or against)
   - Don't change the core claim or make it obviously true/false
   - Maintain the original controversy and scope

## EXAMPLES:

**Example 1 - Add temporal context and fix verb tense:**
Input: "Donald Trump can make America great again"
Date: 2016
Output: "In 2016, Donald Trump could make America great again."
Changed: true
Reason: "Added year context, changed 'can' to 'could' for past conditional, added period"

**Example 2 - Past event with correct tense:**
Input: "The West has lost the Middle East"
Date: 2014
Output: "As of 2014, the West had lost the Middle East."
Changed: true
Reason: "Added temporal context, changed 'has lost' to 'had lost' (past perfect), added period"

**Example 3 - Timeless claim gets temporal context:**
Input: "Men are obsolete"
Date: 2013
Output: "In the context of 2013, men were obsolete."
Changed: true
Reason: "Added temporal framing, used past tense 'were', added period"

**Example 4 - Clarify 'we' and convert question:**
Input: "Do we need a Grand Strategy on China?"
Date: 2021-11-02
Output: "As of 2021, the United States needed a Grand Strategy on China."
Changed: true
Reason: "Added temporal context, converted question to statement, clarified 'we', used past tense, added period"

**Example 5 - Recent debate stays present tense:**
Input: "Will the Future Be Abundant?"
Date: 2023-12-22
Output: "As of 2023, the future will be abundant."
Changed: true
Reason: "Added temporal context, converted question to statement, kept future tense, added period"

**Example 6 - Imperative with temporal context:**
Input: "Tax the rich more"
Date: 2013
Output: "As of 2013, governments should tax the rich more."
Changed: true
Reason: "Added temporal context and subject ('governments'), converted imperative to clear statement, added period"

## RESPONSE FORMAT:
Return JSON with:
{
    "motion": "The cleaned motion text",
    "changed": true/false,
    "reason": "Brief explanation of what changed or why no changes"
}

## CRITICAL REQUIREMENTS:
1. **ALWAYS add temporal context** - Every motion needs a year/date reference
2. **ALWAYS end with a period** - Complete sentences only
3. **ALWAYS use correct verb tenses** - Match the time of the debate
4. **Be consistent** - Apply same standards to all motions

Do not be conservative - actively improve EVERY motion to meet these standards."""


def clean_single_motion(motion_data: dict, model: ModelClient, max_retries: int = 2) -> Optional[dict]:
    """
    Clean a single debate motion using the LLM.

    Args:
        motion_data: Dictionary with motion information
        model: ModelClient instance
        max_retries: Maximum number of retry attempts (default: 2)

    Returns:
        Dict with cleaned motion, changed flag, and reason, or None if processing failed
    """
    original_motion = motion_data.get("motion", "")
    date = motion_data.get("date")
    source = motion_data.get("source", "Unknown")

    if not original_motion:
        return None

    # Build input for LLM
    user_prompt = f"""Clean this debate motion:

ORIGINAL MOTION: {original_motion}
DEBATE DATE: {date if date else "Unknown"}
SOURCE: {source}

Make it standalone and unambiguous while preserving the original meaning.

Return your response in JSON format."""

    # Try up to max_retries times
    import time
    for attempt in range(max_retries):
        try:
            response_text = model.generate(
                get_system_prompt(),
                user_prompt,
                max_tokens=500
            )

            # Parse JSON response
            import re
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    print(f"  Warning: Could not parse JSON from LLM response", file=sys.stderr)
                    if attempt < max_retries - 1:
                        print(f"  Retrying (attempt {attempt + 2}/{max_retries})...", file=sys.stderr)
                        time.sleep(2)
                        continue
                    return None

            # Validate required fields
            required_fields = ["motion", "changed", "reason"]
            if not all(field in result for field in required_fields):
                print(f"  Warning: LLM response missing required fields", file=sys.stderr)
                if attempt < max_retries - 1:
                    print(f"  Retrying (attempt {attempt + 2}/{max_retries})...", file=sys.stderr)
                    time.sleep(2)
                    continue
                return None

            return result

        except Exception as e:
            print(f"  Error processing motion: {e}", file=sys.stderr)
            if attempt < max_retries - 1:
                print(f"  Retrying (attempt {attempt + 2}/{max_retries})...", file=sys.stderr)
                time.sleep(3)  # Longer sleep for API errors
                continue
            return None

    return None


def clean_debate_motions(
    input_file: str,
    output_file: str,
    modifications_file: str,
    model_key: str
) -> None:
    """
    Clean all debate motions in a file.

    Args:
        input_file: Path to input JSON file with collated motions
        output_file: Path to output JSON file for cleaned motions
        modifications_file: Path to modifications log JSON file
        model_key: Model to use for processing
    """
    # Load input data
    print(f"\nLoading debate motions from {input_file}...")
    with open(input_file, 'r') as f:
        motions = json.load(f)

    total_motions = len(motions)
    print(f"Found {total_motions} motions to clean.\n")

    # Initialize model
    print(f"Initializing {MODELS[model_key]['name']}...")
    try:
        model = ModelClient(model_key)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Process motions
    cleaned_motions = []
    modifications = []
    unchanged_count = 0
    changed_count = 0

    print(f"\nCleaning motions...\n")

    for i, motion_data in enumerate(motions):
        motion_num = i + 1
        original_motion = motion_data.get("motion", "")
        print(f"[{motion_num}/{total_motions}] Cleaning motion...")
        print(f"  Original: {original_motion[:80]}...")

        result = clean_single_motion(motion_data, model)

        if result is None:
            print(f"  ✗ Failed to process, keeping original\n")
            cleaned_motions.append(motion_data)
            unchanged_count += 1
            continue

        # Create new motion data with cleaned text
        new_motion_data = motion_data.copy()
        new_motion_data["motion"] = result["motion"]

        if result["changed"]:
            print(f"  ✓ Changed: {result['motion'][:80]}...")
            print(f"    Reason: {result['reason']}\n")
            changed_count += 1

            # Log modification
            modifications.append({
                "index": i,
                "original_motion": original_motion,
                "cleaned_motion": result["motion"],
                "reason": result["reason"],
                "date": motion_data.get("date"),
                "source": motion_data.get("source")
            })
        else:
            print(f"  → Unchanged: {result['reason']}\n")
            unchanged_count += 1

        cleaned_motions.append(new_motion_data)

    # Save cleaned motions
    print(f"\nSaving cleaned motions to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(cleaned_motions, f, indent=2)

    # Save modifications log
    print(f"Saving modifications log to {modifications_file}...")
    with open(modifications_file, 'w') as f:
        json.dump(modifications, f, indent=2)

    # Summary
    print("\n" + "=" * 80)
    print("CLEANING COMPLETE")
    print("=" * 80)
    print(f"\nTotal motions processed: {total_motions}")
    print(f"  ✓ Changed: {changed_count}")
    print(f"  → Unchanged: {unchanged_count}")
    print(f"\nOutput files:")
    print(f"  Cleaned motions: {output_file}")
    print(f"  Modifications log: {modifications_file}")
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Clean debate motions to be standalone and unambiguous",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  python clean_debate_motions.py data/debate-podcasts/debate_motions_collated.json

  python clean_debate_motions.py data/debate-podcasts/debate_motions_collated.json --model gpt4

Available models: {', '.join(MODELS.keys())}

The script will:
1. Read collated debate motions
2. Rewrite each motion to be standalone and unambiguous
3. Add temporal context where relevant (e.g., years for political debates)
4. Clarify ambiguous references (e.g., "we" → "the United States")
5. Convert questions to statements
6. Log all modifications for transparency
7. Output cleaned motions to data/debate_motions.json
        """
    )

    parser.add_argument(
        "input_file",
        nargs='?',
        default="data/debate-podcasts/debate_motions_collated.json",
        help="Input JSON file with collated motions (default: data/debate-podcasts/debate_motions_collated.json)"
    )

    parser.add_argument(
        "--model",
        default="claude",
        choices=list(MODELS.keys()),
        help="Model to use for cleaning (default: claude)"
    )

    parser.add_argument(
        "-o", "--output",
        default="data/debate_motions.json",
        help="Output JSON file for cleaned motions (default: data/debate_motions.json)"
    )

    parser.add_argument(
        "--modifications",
        default="data/debate-podcasts/debate_motions.modifications.json",
        help="Modifications log file (default: data/debate-podcasts/debate_motions.modifications.json)"
    )

    args = parser.parse_args()

    # Validate input file exists
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found", file=sys.stderr)
        sys.exit(1)

    # Clean motions
    try:
        clean_debate_motions(
            args.input_file,
            args.output,
            args.modifications,
            args.model
        )
    except KeyboardInterrupt:
        print("\n\nCleaning interrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
