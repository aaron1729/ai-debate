#!/usr/bin/env python3
"""
Validate experiment results JSON files to ensure they have correct structure and values.

Expected schema:
- claim_data: {claim: str, topic: str (optional)}
- ground_truth: {verdict: str (optional), source: str (optional), url: str/null (optional)}
- experiment_config: {timestamp: str, models: {pro: str, con: str, judge: str}, turns: int, pro_went_first: bool}
- debate_transcript: list of {turn: int, debater: "pro"|"con", argument: str, source_url: str, source_quote: str, refused?: bool, refusal_reason?: str}
- judge_decision: {verdict: str, score: int (-1 or 0-10), reasoning: str}
- errors_or_refusals: list
"""

import json
import sys
from pathlib import Path
from datetime import datetime

VALID_VERDICTS = ["supported", "contradicted", "misleading", "needs more evidence"]
VALID_DEBATER_POSITIONS = ["pro", "con"]

def load_topics(topics_file="topics.json"):
    """Load valid topics from topics.json"""
    try:
        with open(topics_file, 'r') as f:
            topics = json.load(f)
            if not isinstance(topics, list):
                print(f"Warning: {topics_file} should contain a JSON array")
                return []
            return topics
    except FileNotFoundError:
        print(f"Warning: {topics_file} not found, skipping topic validation")
        return []
    except json.JSONDecodeError as e:
        print(f"Warning: Error parsing {topics_file}: {e}")
        return []

def validate_experiment(exp_file, valid_topics):
    """Validate an experiment results JSON file"""
    print(f"\nValidating {exp_file}...")

    try:
        with open(exp_file, 'r') as f:
            exp = json.load(f)
    except FileNotFoundError:
        print(f"  ✗ Error: File not found")
        return False
    except json.JSONDecodeError as e:
        print(f"  ✗ Error: Invalid JSON - {e}")
        return False

    if not isinstance(exp, dict):
        print(f"  ✗ Error: Root element should be a JSON object")
        return False

    errors = []
    warnings = []

    # Check for required top-level fields
    required_fields = ["claim_data", "ground_truth", "experiment_config",
                       "debate_transcript", "judge_decision", "errors_or_refusals"]
    missing_fields = [field for field in required_fields if field not in exp]
    if missing_fields:
        errors.append(f"Missing top-level fields: {missing_fields}")
        print(f"  ✗ Found {len(errors)} error(s):")
        for error in errors:
            print(f"    {error}")
        return False

    # Validate claim_data
    if not isinstance(exp["claim_data"], dict):
        errors.append("claim_data must be an object")
    else:
        if "claim" not in exp["claim_data"]:
            errors.append("claim_data missing 'claim' field")
        elif not isinstance(exp["claim_data"]["claim"], str):
            errors.append("claim_data.claim must be a string")

        if "topic" in exp["claim_data"]:
            if not isinstance(exp["claim_data"]["topic"], str):
                errors.append("claim_data.topic must be a string")
            elif valid_topics and exp["claim_data"]["topic"] not in valid_topics:
                errors.append(f"Invalid topic '{exp['claim_data']['topic']}'. Must be one of {valid_topics}")

    # Validate ground_truth
    if not isinstance(exp["ground_truth"], dict):
        errors.append("ground_truth must be an object")
    else:
        if "verdict" in exp["ground_truth"]:
            if not isinstance(exp["ground_truth"]["verdict"], str):
                errors.append("ground_truth.verdict must be a string")
            elif exp["ground_truth"]["verdict"] not in VALID_VERDICTS:
                errors.append(f"Invalid ground_truth verdict '{exp['ground_truth']['verdict']}'")

        if "source" in exp["ground_truth"] and not isinstance(exp["ground_truth"]["source"], str):
            errors.append("ground_truth.source must be a string")

        if "url" in exp["ground_truth"] and exp["ground_truth"]["url"] is not None:
            if not isinstance(exp["ground_truth"]["url"], str):
                errors.append("ground_truth.url must be a string or null")

    # Validate experiment_config
    if not isinstance(exp["experiment_config"], dict):
        errors.append("experiment_config must be an object")
    else:
        config_required = ["timestamp", "models", "turns", "pro_went_first"]
        config_missing = [f for f in config_required if f not in exp["experiment_config"]]
        if config_missing:
            errors.append(f"experiment_config missing fields: {config_missing}")

        # Validate timestamp
        if "timestamp" in exp["experiment_config"]:
            if not isinstance(exp["experiment_config"]["timestamp"], str):
                errors.append("experiment_config.timestamp must be a string")
            else:
                try:
                    datetime.fromisoformat(exp["experiment_config"]["timestamp"].replace('Z', '+00:00'))
                except ValueError:
                    errors.append(f"Invalid timestamp format: {exp['experiment_config']['timestamp']}")

        # Validate models
        if "models" in exp["experiment_config"]:
            if not isinstance(exp["experiment_config"]["models"], dict):
                errors.append("experiment_config.models must be an object")
            else:
                model_required = ["pro", "con", "judge"]
                model_missing = [f for f in model_required if f not in exp["experiment_config"]["models"]]
                if model_missing:
                    errors.append(f"experiment_config.models missing: {model_missing}")

        # Validate turns
        if "turns" in exp["experiment_config"]:
            if not isinstance(exp["experiment_config"]["turns"], int):
                errors.append("experiment_config.turns must be an integer")
            elif exp["experiment_config"]["turns"] < 1:
                errors.append("experiment_config.turns must be at least 1")

        # Validate pro_went_first
        if "pro_went_first" in exp["experiment_config"]:
            if not isinstance(exp["experiment_config"]["pro_went_first"], bool):
                errors.append("experiment_config.pro_went_first must be a boolean")

    # Validate debate_transcript
    if not isinstance(exp["debate_transcript"], list):
        errors.append("debate_transcript must be an array")
    else:
        for i, entry in enumerate(exp["debate_transcript"], 1):
            if not isinstance(entry, dict):
                errors.append(f"Transcript entry {i}: Not an object")
                continue

            # Check required fields
            trans_required = ["turn", "debater", "argument", "source_url", "source_quote"]
            trans_missing = [f for f in trans_required if f not in entry]
            if trans_missing:
                errors.append(f"Transcript entry {i}: Missing fields {trans_missing}")

            # Validate field types
            if "turn" in entry and not isinstance(entry["turn"], int):
                errors.append(f"Transcript entry {i}: turn must be an integer")

            if "debater" in entry:
                if not isinstance(entry["debater"], str):
                    errors.append(f"Transcript entry {i}: debater must be a string")
                elif entry["debater"] not in VALID_DEBATER_POSITIONS:
                    errors.append(f"Transcript entry {i}: Invalid debater '{entry['debater']}'. Must be 'pro' or 'con'")

            # Check refusal fields if present
            if entry.get("refused", False):
                if not isinstance(entry["refused"], bool):
                    errors.append(f"Transcript entry {i}: refused must be a boolean")
                if "refusal_reason" not in entry:
                    warnings.append(f"Transcript entry {i}: Has refused=true but no refusal_reason")

    # Validate judge_decision
    if not isinstance(exp["judge_decision"], dict):
        errors.append("judge_decision must be an object")
    else:
        judge_required = ["verdict", "score", "reasoning"]
        judge_missing = [f for f in judge_required if f not in exp["judge_decision"]]
        if judge_missing:
            errors.append(f"judge_decision missing fields: {judge_missing}")

        if "verdict" in exp["judge_decision"]:
            if not isinstance(exp["judge_decision"]["verdict"], str):
                errors.append("judge_decision.verdict must be a string")
            elif exp["judge_decision"]["verdict"] not in VALID_VERDICTS:
                errors.append(f"Invalid judge verdict '{exp['judge_decision']['verdict']}'")

        if "score" in exp["judge_decision"]:
            if not isinstance(exp["judge_decision"]["score"], int):
                errors.append("judge_decision.score must be an integer")
            elif exp["judge_decision"]["score"] not in range(-1, 11):
                errors.append(f"judge_decision.score must be -1 or 0-10, got {exp['judge_decision']['score']}")

            # Validate score matches verdict
            if "verdict" in exp["judge_decision"]:
                if exp["judge_decision"]["verdict"] == "needs more evidence" and exp["judge_decision"]["score"] != -1:
                    errors.append(f"Verdict 'needs more evidence' must have score -1, got {exp['judge_decision']['score']}")

        if "reasoning" in exp["judge_decision"] and not isinstance(exp["judge_decision"]["reasoning"], str):
            errors.append("judge_decision.reasoning must be a string")

    # Validate errors_or_refusals
    if not isinstance(exp["errors_or_refusals"], list):
        errors.append("errors_or_refusals must be an array")

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
        print(f"  ✓ Experiment file is valid!")
        return True
    elif not errors:
        print(f"  ✓ No errors found (only warnings)")
        return True
    else:
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_experiment_json.py <experiment_file.json> [<experiment_file2.json> ...]")
        print("\nExample: python validate_experiment_json.py experiment_schema_example.json")
        sys.exit(1)

    # Load valid topics
    valid_topics = load_topics()
    if valid_topics:
        print(f"Valid topics: {valid_topics}")
    print(f"Valid verdicts: {VALID_VERDICTS}")

    # Validate each file
    all_valid = True
    for exp_file in sys.argv[1:]:
        if not validate_experiment(exp_file, valid_topics):
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
