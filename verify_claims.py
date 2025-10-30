#!/usr/bin/env python3
"""
Claim Verification Script
Verifies cleaned claims by fetching URLs and having an LLM check if claims match the source content.
Can modify claims, verdicts, topics, or delete unsuitable claims.
"""

import os
import sys
import json
import argparse
import requests
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

# Import from other scripts
from debate import ModelClient, MODELS


def fetch_url_content(url: str) -> Optional[str]:
    """
    Fetch and extract text content from a URL.

    Args:
        url: URL to fetch

    Returns:
        Extracted text content from the webpage, or None if fetch failed
    """
    try:
        # Set a reasonable timeout and user agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # Fetch the URL with timeout
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise exception for bad status codes

        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()

        # Get text content
        text = soup.get_text()

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)

        # Limit to reasonable length (first ~3000 chars for context)
        if len(text) > 3000:
            text = text[:3000] + "..."

        return text

    except requests.exceptions.Timeout:
        print(f"  Warning: URL fetch timed out: {url}", file=sys.stderr)
        return None
    except requests.exceptions.RequestException as e:
        print(f"  Warning: Could not fetch URL: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Warning: Error processing URL content: {e}", file=sys.stderr)
        return None


def get_verification_prompt(topics: list[str]) -> str:
    """Generate the system prompt for claim verification."""
    topics_str = ", ".join(f'"{t}"' for t in topics)

    return f"""You are a claim verification assistant. Your task is to review cleaned fact-check claims and ensure they are:
1. Specific and factually debatable
2. Accurately match the fact-checker's article content
3. Include necessary temporal/geographical context
4. Have correct verdict and topic assignments

You will receive:
- A claim text
- The fact-checker's original rating
- The URL to the fact-check article
- Current verdict and topic assignments
- (Optionally) A summary of the URL content

## YOUR TASK:
Review the claim and determine if it needs changes.

## VALID VERDICTS:
1. "supported" - Claim is well-supported by evidence
2. "contradicted" - Claim is contradicted by evidence
3. "misleading" - Technically true but misleading or lacks important context
4. "needs more evidence" - Insufficient evidence to determine truth

## VALID TOPICS:
Current topics: [{topics_str}]
You can also suggest new broad topics if needed (lowercase, simple).

## QUALITY CRITERIA:

**Good claims are:**
- Specific and concrete (not vague like "Scientists paused research")
- Include dates/locations when relevant ("in January 2025", "in Los Angeles")
- Factually debatable (not pure opinion)
- Standalone - readable without additional context
- Accurately represent what the fact-checker reviewed

**Bad claims need fixing:**
- Too vague: "Scientists have had to pause the Climate Change Hoax Scam"
  → Should specify what actually happened based on the article
- Missing context: "The first snowfall occurred"
  → Needs location and date
- Don't match URL: Claim about X but article is about Y
- Wrong verdict: Rated "False" but verdict is "supported"

## EXAMPLES:

**Example 1 - Needs modification:**
Claim: "Scientists have had to pause the Climate Change Hoax Scam"
URL: Article about Antarctic ice study being misinterpreted
Rating: "Misleading"
Verdict: "misleading"

Issue: Claim is vague and doesn't match article content.

Response:
{{
    "action": "modify",
    "claim": "Climate change deniers misinterpreted a 2025 Antarctic ice study to falsely claim that scientists have paused climate change research",
    "verdict": "misleading",
    "topic": "climate",
    "reason": "Original claim was too vague. Rewrote based on article content about Antarctic ice study misinterpretation."
}}

**Example 2 - Keep unchanged:**
Claim: "Antarctic sea ice extent is 17 percent higher in December 2024 compared to 1979"
URL: Article about cherry-picked Antarctic ice data
Rating: "Misleading"
Verdict: "misleading"

Response:
{{
    "action": "keep",
    "reason": "Claim is specific, includes date, matches article content, and verdict is correct."
}}

**Example 3 - Delete:**
Claim: "CLAIM"
URL: 404 error / unrelated content

Response:
{{
    "action": "delete",
    "reason": "Claim text is placeholder and URL is not accessible."
}}

**Example 4 - Fix verdict:**
Claim: "US Climate Reference Network data shows no obvious warming since 2005"
URL: Article debunking the claim
Rating: "False"
Current verdict: "supported"

Response:
{{
    "action": "modify",
    "claim": "US Climate Reference Network data shows no obvious warming since 2005",
    "verdict": "contradicted",
    "topic": "climate",
    "reason": "Verdict was incorrect - fact-checker rated this 'False' so it should be 'contradicted', not 'supported'."
}}

## RESPONSE FORMAT:

If claim is good as-is:
{{
    "action": "keep",
    "reason": "Brief explanation why it's acceptable"
}}

If claim needs modification:
{{
    "action": "modify",
    "claim": "Improved claim text",
    "verdict": "one of the 4 verdicts",
    "topic": "topic name",
    "reason": "Explanation of what was changed and why"
}}

If claim should be deleted:
{{
    "action": "delete",
    "reason": "Explanation why claim is unsalvageable"
}}

Be thorough but fair. Only modify when there's a clear issue. Preserve good claims."""


def verify_single_claim(claim_data: dict, model: ModelClient, topics: list[str]) -> dict:
    """
    Verify a single claim using the LLM.

    Returns:
        Dict with action (keep/modify/delete) and details
    """
    # Fetch URL content
    url_content = fetch_url_content(claim_data['url'])

    # Build verification prompt
    user_prompt = f"""Review this claim for quality and accuracy:

CLAIM: {claim_data['claim']}
CLAIM DATE: {claim_data['claimDate']}
PUBLISHER: {claim_data['publisher']}
URL: {claim_data['url']}
CURRENT VERDICT: {claim_data['verdict']}
CURRENT TOPIC: {claim_data['topic']}

"""

    if url_content:
        user_prompt += f"""URL CONTENT (excerpt from fact-check article):
{url_content}

Based on the URL content, verify if this claim is:
"""
    else:
        user_prompt += """Note: Could not fetch URL content. Based on the claim text and your knowledge, verify if this claim is:
"""

    user_prompt += """1. Specific and factually debatable
2. Includes necessary temporal/geographical context
3. Has the correct verdict mapping (based on the article content)
4. Has the correct topic

Return your response in JSON format with action (keep/modify/delete)."""

    try:
        response_text = model.generate(
            get_verification_prompt(topics),
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
                return {"action": "keep", "reason": "Parse error - keeping original"}

        # Validate action
        valid_actions = ["keep", "modify", "delete"]
        if result.get("action") not in valid_actions:
            print(f"  Warning: Invalid action '{result.get('action')}'", file=sys.stderr)
            return {"action": "keep", "reason": "Invalid action - keeping original"}

        return result

    except Exception as e:
        print(f"  Error verifying claim: {e}", file=sys.stderr)
        return {"action": "keep", "reason": f"Error during verification: {e}"}


def verify_claims_file(input_file: str, output_file: str, model_key: str, topics_file: str = "topics.json") -> None:
    """
    Verify all claims in a file.

    Args:
        input_file: Path to cleaned claims JSON
        output_file: Path to output verified claims JSON
        model_key: Model to use for verification
        topics_file: Path to topics.json
    """
    # Load input data
    print(f"\nLoading claims from {input_file}...")
    with open(input_file, 'r') as f:
        claims = json.load(f)

    total_claims = len(claims)
    print(f"Found {total_claims} claims to verify.\n")

    # Load topics
    if os.path.exists(topics_file):
        with open(topics_file, 'r') as f:
            topics = json.load(f)
    else:
        topics = ["climate", "health", "politics", "science", "technology", "economics"]

    print(f"Using {len(topics)} topics: {', '.join(topics)}\n")

    # Initialize model
    print(f"Initializing {MODELS[model_key]['name']}...")
    try:
        model = ModelClient(model_key)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Load existing results if resuming
    verified_claims = []
    modifications_log = []
    start_index = 0

    modifications_file = f"{output_file}_modifications.json"

    if os.path.exists(output_file):
        print(f"\nFound existing output file, resuming from where we left off...")
        with open(output_file, 'r') as f:
            verified_claims = json.load(f)
        start_index = len(verified_claims)

    if os.path.exists(modifications_file):
        with open(modifications_file, 'r') as f:
            modifications_log = json.load(f)

    # Verify claims
    print(f"\nVerifying claims {start_index + 1}-{total_claims}...\n")

    stats = {"kept": 0, "modified": 0, "deleted": 0}

    for i in range(start_index, total_claims):
        claim_num = i + 1
        claim_data = claims[i]

        print(f"[{claim_num}/{total_claims}] Verifying: {claim_data['claim'][:80]}...")

        result = verify_single_claim(claim_data, model, topics)

        if result["action"] == "keep":
            print(f"  ✓ Keeping unchanged")
            print(f"    Reason: {result.get('reason', 'No issues found')}\n")
            verified_claims.append(claim_data)
            stats["kept"] += 1

        elif result["action"] == "modify":
            print(f"  ↻ Modifying claim")
            print(f"    Reason: {result.get('reason', 'Improvements needed')}")

            # Log modification
            modification_entry = {
                "timestamp": datetime.now().isoformat(),
                "original": claim_data.copy(),
                "modified": {
                    "claim": result.get("claim", claim_data["claim"]),
                    "verdict": result.get("verdict", claim_data["verdict"]),
                    "topic": result.get("topic", claim_data["topic"])
                },
                "reason": result.get("reason", "No reason provided")
            }
            modifications_log.append(modification_entry)

            # Create modified claim
            modified_claim = claim_data.copy()
            modified_claim["claim"] = result.get("claim", claim_data["claim"])
            modified_claim["verdict"] = result.get("verdict", claim_data["verdict"])
            modified_claim["topic"] = result.get("topic", claim_data["topic"])

            print(f"    New claim: {modified_claim['claim'][:80]}...\n")
            verified_claims.append(modified_claim)
            stats["modified"] += 1

        elif result["action"] == "delete":
            print(f"  ✗ Deleting claim")
            print(f"    Reason: {result.get('reason', 'Unsalvageable')}\n")

            # Log deletion
            deletion_entry = {
                "timestamp": datetime.now().isoformat(),
                "original": claim_data.copy(),
                "deleted": True,
                "reason": result.get("reason", "No reason provided")
            }
            modifications_log.append(deletion_entry)
            stats["deleted"] += 1

        # Save progress after each claim
        with open(output_file, 'w') as f:
            json.dump(verified_claims, f, indent=2)

        with open(modifications_file, 'w') as f:
            json.dump(modifications_log, f, indent=2)

    # Summary
    print("=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)
    print(f"\nTotal claims processed: {total_claims}")
    print(f"  ✓ Kept unchanged: {stats['kept']}")
    print(f"  ↻ Modified: {stats['modified']}")
    print(f"  ✗ Deleted: {stats['deleted']}")
    print(f"\nFinal count: {len(verified_claims)} verified claims")
    print(f"\nOutput files:")
    print(f"  Verified claims: {output_file}")
    print(f"  Modifications log: {modifications_file}")
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify cleaned claims by checking against source URLs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  python verify_claims.py test_clean_climate.json -o climate_verified.json
  python verify_claims.py clean_health.json --model gpt4 -o health_verified.json

Available models: {', '.join(MODELS.keys())}

The script will:
1. Read each cleaned claim
2. Verify claim quality (specificity, context, accuracy)
3. Check verdict and topic assignments
4. Keep, modify, or delete claims as needed
5. Log all modifications transparently
6. Save progress after each claim (safe to interrupt and resume)
        """
    )

    parser.add_argument(
        "input_file",
        help="Input JSON file with cleaned claims (e.g., test_clean_climate.json)"
    )

    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Output JSON file for verified claims"
    )

    parser.add_argument(
        "--model",
        default="claude",
        choices=list(MODELS.keys()),
        help="Model to use for verification (default: claude)"
    )

    parser.add_argument(
        "--topics-file",
        default="topics.json",
        help="Topics file to reference (default: topics.json)"
    )

    args = parser.parse_args()

    # Validate input file exists
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found", file=sys.stderr)
        sys.exit(1)

    # Verify claims
    try:
        verify_claims_file(args.input_file, args.output, args.model, args.topics_file)
    except KeyboardInterrupt:
        print("\n\nVerification interrupted by user. Progress has been saved.", file=sys.stderr)
        print("Run the same command again to resume from where you left off.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
