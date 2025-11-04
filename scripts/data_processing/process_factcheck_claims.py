#!/usr/bin/env python3
"""
Claim Processing Script
Cleans and standardizes fact-checked claims using an LLM to prepare them for debate testing.
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


def load_topics(topics_file: str = "topics.json") -> list[str]:
    """Load existing topics from JSON file, or create with defaults."""
    if os.path.exists(topics_file):
        with open(topics_file, 'r') as f:
            topics = json.load(f)
        return topics
    else:
        # Default starter topics
        default_topics = ["climate", "health", "politics", "science", "technology", "economics"]
        save_topics(default_topics, topics_file)
        return default_topics


def save_topics(topics: list[str], topics_file: str = "topics.json") -> None:
    """Save topics list to JSON file."""
    with open(topics_file, 'w') as f:
        json.dump(sorted(set(topics)), f, indent=2)


def get_system_prompt(topics: list[str]) -> str:
    """Generate the system prompt for claim processing."""
    topics_str = ", ".join(f'"{t}"' for t in topics)

    return f"""You are a claim processing assistant. Your task is to clean and standardize fact-checked claims for use in an AI debate system.

For each claim, you must:
1. Rewrite the claim to be standalone and debatable (if needed)
2. Map the fact-checker's rating to one of 4 standard verdicts
3. Assign a topic from the existing list (or create a new broad topic if needed)
4. Filter out unsuitable claims

## VALID VERDICTS (must match exactly):
1. "supported" - Claim is well-supported by evidence
2. "contradicted" - Claim is contradicted by evidence
3. "misleading" - Technically true but misleading or lacks important context
4. "needs more evidence" - Insufficient evidence to determine truth

## VERDICT MAPPING GUIDELINES:
Map fact-checker ratings to verdicts as follows:

**"contradicted":**
- "False", "Incorrect", "Fake", "Totally False", "Not true"
- "AI-generated" (when debunking a claim)
- Any clear debunking

**"supported":**
- "True", "Correct", "Correct Attribution"
- "Mostly True" (if claim is substantially accurate)

**"misleading":**
- "Misleading", "Missing context", "Needs Context"
- "Partly false", "Partly true", "Half True"
- "Exaggerates", "Overstates"
- Claims with significant context issues

**"needs more evidence":**
- "Mixture", "Mixed", "Unsubstantiated"
- "Unsupported", "Inconclusive"
- "Unproven"

## TOPICS:
Current topics: [{topics_str}]

Guidelines:
- Prefer existing topics when possible
- Keep topics BROAD (e.g., "climate" not "antarctic ice")
- Topics should be lowercase, single words or short phrases
- Only create new topic if claim clearly doesn't fit any existing category
- Common new topics might be: "vaccines", "energy", "food", "environment", etc.

## CLAIM REWRITING:
Make claims standalone and debatable by including all necessary context.

**Guidelines for standalone claims:**
- Include specific dates/years when the claim is about a particular time period or event
- Add location specificity when relevant (city, country, region)
- Ensure someone reading ONLY the claim text (without any other context) can fully understand what's being asserted
- Use information from the review title, claim date, and review date to add necessary temporal/geographical context
- Make claims precise enough to debate without requiring additional background

**Good rewrites with temporal/geographical context:**

- "Antarctic sea ice extent is 17 per cent higher today compared to 1979"
  + Claim date: December 2024
  → "Antarctic sea ice extent in December 2024 is 17 percent higher than it was in 1979"

- "The first-ever snowfall in the Al-Jouf desert" (incomplete)
  + Claim date: November 2024
  → "The first-ever snowfall in the Al-Jouf desert in Saudi Arabia occurred in November 2024"

- "Climate change had no influence on wildfires"
  + Review title mentions Los Angeles, claim date January 2025
  → "Climate change had no influence on the Los Angeles wildfires in January 2025"

- "An established scientific theory shows a key driver of climate change is impossible"
  + Review title: "No, ideal gas law doesn't debunk climate change"
  → "The ideal gas law proves that human-caused climate change is impossible"

- "CLAIM" (with review about coffee and longevity)
  → "Coffee consumption increases human lifespan"

- "US Climate Reference Network data shows 'no obvious warming' since 2005"
  → (Already good - includes the timeframe "since 2005")

**Skip these (return null):**
- Viral video claims without clear text ("CLAIM:" with just video description)
- Pure opinion pieces without factual claims
- Claims too vague to debate even with context
- Claims about specific local events unlikely to be debatable
- Non-English claims (though these should already be filtered)

## RESPONSE FORMAT:
If the claim should be processed, return:
{{
    "claim": "Rewritten standalone claim text",
    "claimDate": "2025-10-15T00:00:00Z",
    "publisher": "Fact-checker name",
    "url": "https://...",
    "verdict": "one of the 4 verdicts",
    "topic": "topic from list or new topic"
}}

If the claim should be skipped, return:
{{
    "skip": true,
    "reason": "Brief explanation why this claim should be skipped"
}}

## EXAMPLES:

**Example 1 - Process:**
Input claim: "Climate not to blame for houses collapsing in North Carolina"
Rating: "Misleading"
Review title: "US homes collapse into sea, sparking climate debate online"

Response:
{{
    "claim": "Climate change is not to blame for houses collapsing into the sea in North Carolina",
    "claimDate": "2025-09-18T00:00:00Z",
    "publisher": "AFP Fact Check",
    "url": "https://factcheck.afp.com/doc.afp.com.76TC4G3",
    "verdict": "misleading",
    "topic": "climate"
}}

**Example 2 - Skip:**
Input claim: "CLAIM"
Review about a viral video showing something
Response:
{{
    "skip": true,
    "reason": "Claim text is just placeholder 'CLAIM' referring to viral video without clear factual assertion"
}}

**Example 3 - New Topic:**
Input claim about cryptocurrency regulation
Topics list doesn't include "cryptocurrency" or "finance"
Response includes: "topic": "finance" (new broad topic)

Be rigorous but fair. When in doubt about verdict mapping, prefer "misleading" or "needs more evidence" over hard "supported"/"contradicted"."""


def process_single_claim(raw_claim: dict, model: ModelClient, topics: list[str]) -> Optional[dict]:
    """
    Process a single claim using the LLM.

    Returns:
        Processed claim dict, or None if claim should be skipped
    """
    # Extract first English claim review
    claim_reviews = raw_claim.get("claimReview", [])
    if not claim_reviews:
        return None

    # Find first English review
    english_review = None
    for review in claim_reviews:
        if review.get("languageCode") == "en":
            english_review = review
            break

    if not english_review:
        return None

    # Build input for LLM
    user_prompt = f"""Process this claim:

CLAIM TEXT: {raw_claim.get('text', 'CLAIM')}
CLAIMANT: {raw_claim.get('claimant', 'Unknown')}
CLAIM DATE: {raw_claim.get('claimDate', '')}

FACT-CHECK REVIEW:
Publisher: {english_review['publisher']['name']}
URL: {english_review['url']}
Review Title: {english_review.get('title', '')}
Rating: {english_review.get('textualRating', '')}
Review Date: {english_review.get('reviewDate', '')}

Return your response in JSON format."""

    # Call LLM
    try:
        response_text = model.generate(
            get_system_prompt(topics),
            user_prompt,
            max_tokens=1000
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
                return None

        # Check if LLM says to skip
        if result.get("skip", False):
            return {"skipped": True, "reason": result.get("reason", "No reason provided")}

        # Validate required fields
        required_fields = ["claim", "claimDate", "publisher", "url", "verdict", "topic"]
        if not all(field in result for field in required_fields):
            print(f"  Warning: LLM response missing required fields", file=sys.stderr)
            return None

        # Validate verdict
        valid_verdicts = ["supported", "contradicted", "misleading", "needs more evidence"]
        if result["verdict"] not in valid_verdicts:
            print(f"  Warning: Invalid verdict '{result['verdict']}', skipping", file=sys.stderr)
            return None

        # Check if new topic was added
        topic = result["topic"].lower().strip()
        if topic not in topics:
            topics.append(topic)
            print(f"  → New topic added: '{topic}'")

        result["topic"] = topic
        return result

    except Exception as e:
        print(f"  Error processing claim: {e}", file=sys.stderr)
        return None


def process_claims_file(input_file: str, output_file: str, model_key: str, topics_file: str = "topics.json") -> None:
    """
    Process all claims in a file.

    Args:
        input_file: Path to input JSON file with raw claims
        output_file: Path to output JSON file for cleaned claims
        model_key: Model to use for processing
        topics_file: Path to topics.json file
    """
    # Load input data
    print(f"\nLoading claims from {input_file}...")
    with open(input_file, 'r') as f:
        data = json.load(f)

    raw_claims = data.get("claims", [])
    total_claims = len(raw_claims)
    print(f"Found {total_claims} claims to process.\n")

    # Load topics
    topics = load_topics(topics_file)
    print(f"Loaded {len(topics)} existing topics: {', '.join(topics)}\n")

    # Initialize model
    print(f"Initializing {MODELS[model_key]['name']}...")
    try:
        model = ModelClient(model_key)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Load existing results if resuming
    processed_claims = []
    skipped_claims = []
    start_index = 0

    if os.path.exists(output_file):
        print(f"\nFound existing output file, resuming from where we left off...")
        with open(output_file, 'r') as f:
            processed_claims = json.load(f)
        start_index = len(processed_claims)

    if os.path.exists(f"{output_file}.skipped.json"):
        with open(f"{output_file}.skipped.json", 'r') as f:
            skipped_claims = json.load(f)

    # Process claims
    print(f"\nProcessing claims {start_index + 1}-{total_claims}...\n")

    for i in range(start_index, total_claims):
        claim_num = i + 1
        print(f"[{claim_num}/{total_claims}] Processing claim...")

        result = process_single_claim(raw_claims[i], model, topics)

        if result is None:
            print(f"  ✗ Skipped (parsing error or missing data)\n")
            skipped_claims.append({
                "original_text": raw_claims[i].get("text", ""),
                "reason": "Processing error or missing data"
            })
        elif result.get("skipped", False):
            print(f"  ✗ Skipped: {result['reason']}\n")
            skipped_claims.append({
                "original_text": raw_claims[i].get("text", ""),
                "reason": result["reason"]
            })
        else:
            print(f"  ✓ Processed: {result['claim'][:80]}...")
            print(f"    Verdict: {result['verdict']} | Topic: {result['topic']}\n")
            processed_claims.append(result)

        # Save progress after each claim
        with open(output_file, 'w') as f:
            json.dump(processed_claims, f, indent=2)

        with open(f"{output_file}.skipped.json", 'w') as f:
            json.dump(skipped_claims, f, indent=2)

        # Save updated topics
        save_topics(topics, topics_file)

    # Summary
    print("=" * 80)
    print("PROCESSING COMPLETE")
    print("=" * 80)
    print(f"\nTotal claims processed: {total_claims}")
    print(f"  ✓ Kept: {len(processed_claims)}")
    print(f"  ✗ Skipped: {len(skipped_claims)}")
    print(f"\nOutput files:")
    print(f"  Processed claims: {output_file}")
    print(f"  Skipped claims: {output_file}.skipped.json")
    print(f"  Topics: {topics_file}")
    print(f"\nFinal topic list ({len(topics)} topics): {', '.join(sorted(topics))}")
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Process fact-checked claims for AI debate testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  python process_factcheck_claims.py data/google-fact-check/raw/claims_historical_climate_50.json -o data/google-fact-check/cleaned/clean_climate.json
  python process_factcheck_claims.py data/google-fact-check/raw/claims_historical_health_50.json --model gpt4 -o data/google-fact-check/cleaned/clean_health.json

Available models: {', '.join(MODELS.keys())}

The script will:
1. Clean and rewrite claims to be standalone and debatable
2. Map fact-checker ratings to standard verdicts (supported/contradicted/misleading/needs more evidence)
3. Assign topics from existing list or create new ones
4. Filter out unsuitable claims (viral videos, vague claims, etc.)
5. Save progress after each claim (safe to interrupt and resume)
        """
    )

    parser.add_argument(
        "input_file",
        help="Input JSON file with raw claims (e.g., claims_historical_climate_50.json)"
    )

    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Output JSON file for cleaned claims"
    )

    parser.add_argument(
        "--model",
        default="claude",
        choices=list(MODELS.keys()),
        help="Model to use for processing (default: claude)"
    )

    parser.add_argument(
        "--topics-file",
        default="topics.json",
        help="Topics file to use/update (default: topics.json)"
    )

    args = parser.parse_args()

    # Validate input file exists
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found", file=sys.stderr)
        sys.exit(1)

    # Process claims
    try:
        process_claims_file(args.input_file, args.output, args.model, args.topics_file)
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user. Progress has been saved.", file=sys.stderr)
        print("Run the same command again to resume from where you left off.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
