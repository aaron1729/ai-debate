#!/usr/bin/env python3
"""
Validate claims JSON files to ensure they have correct structure and values.

Each entry should have:
- "claim": string
- "verdict": one of ["supported", "contradicted", "misleading", "needs more evidence"]
- "topic": one of the topics from topics.json
"""

import json
import sys
from pathlib import Path

VALID_VERDICTS = ["supported", "contradicted", "misleading", "needs more evidence"]

def load_topics(topics_file="topics.json"):
    """Load valid topics from topics.json"""
    try:
        with open(topics_file, 'r') as f:
            topics = json.load(f)
            if not isinstance(topics, list):
                print(f"Error: {topics_file} should contain a JSON array")
                sys.exit(1)
            return topics
    except FileNotFoundError:
        print(f"Error: {topics_file} not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing {topics_file}: {e}")
        sys.exit(1)

def validate_claims(claims_file, valid_topics):
    """Validate a claims JSON file"""
    print(f"\nValidating {claims_file}...")

    try:
        with open(claims_file, 'r') as f:
            claims = json.load(f)
    except FileNotFoundError:
        print(f"  ✗ Error: File not found")
        return False
    except json.JSONDecodeError as e:
        print(f"  ✗ Error: Invalid JSON - {e}")
        return False

    if not isinstance(claims, list):
        print(f"  ✗ Error: Root element should be a JSON array")
        return False

    print(f"  Found {len(claims)} entries")

    errors = []
    warnings = []

    for i, claim in enumerate(claims, 1):
        if not isinstance(claim, dict):
            errors.append(f"  Entry {i}: Not a dictionary")
            continue

        # Check for required fields
        required_fields = ["claim", "verdict", "topic"]
        missing_fields = [field for field in required_fields if field not in claim]
        if missing_fields:
            errors.append(f"  Entry {i}: Missing fields: {missing_fields}")
            continue

        # Check field types
        if not isinstance(claim["claim"], str):
            errors.append(f"  Entry {i}: 'claim' must be a string")
        elif not claim["claim"].strip():
            warnings.append(f"  Entry {i}: 'claim' is empty or whitespace")

        if not isinstance(claim["verdict"], str):
            errors.append(f"  Entry {i}: 'verdict' must be a string")
        elif claim["verdict"] not in VALID_VERDICTS:
            errors.append(f"  Entry {i}: Invalid verdict '{claim['verdict']}'. Must be one of {VALID_VERDICTS}")

        if not isinstance(claim["topic"], str):
            errors.append(f"  Entry {i}: 'topic' must be a string")
        elif claim["topic"] not in valid_topics:
            errors.append(f"  Entry {i}: Invalid topic '{claim['topic']}'. Must be one of {valid_topics}")

        # Check for extra fields
        extra_fields = set(claim.keys()) - set(required_fields)
        if extra_fields:
            warnings.append(f"  Entry {i}: Extra fields found: {extra_fields}")

    # Print results
    if errors:
        print(f"\n  ✗ Found {len(errors)} error(s):")
        for error in errors[:10]:  # Show first 10 errors
            print(f"    {error}")
        if len(errors) > 10:
            print(f"    ... and {len(errors) - 10} more errors")

    if warnings:
        print(f"\n  ⚠ Found {len(warnings)} warning(s):")
        for warning in warnings[:10]:  # Show first 10 warnings
            print(f"    {warning}")
        if len(warnings) > 10:
            print(f"    ... and {len(warnings) - 10} more warnings")

    if not errors and not warnings:
        print(f"  ✓ All entries are valid!")
        return True
    elif not errors:
        print(f"  ✓ No errors found (only warnings)")
        return True
    else:
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_claims.py <claims_file.json> [<claims_file2.json> ...]")
        print("\nExample: python validate_claims.py claims_gpt5_01.json")
        sys.exit(1)

    # Load valid topics
    valid_topics = load_topics()
    print(f"Valid topics: {valid_topics}")
    print(f"Valid verdicts: {VALID_VERDICTS}")

    # Validate each file
    all_valid = True
    for claims_file in sys.argv[1:]:
        if not validate_claims(claims_file, valid_topics):
            all_valid = False

    # Exit with appropriate code
    if all_valid:
        print("\n✓ All files are valid!")
        sys.exit(0)
    else:
        print("\n✗ Some files have errors")
        sys.exit(1)

if __name__ == "__main__":
    main()
