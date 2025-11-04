#!/usr/bin/env python3
"""Test script to check Anthropic API connection and available models."""

import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("Error: ANTHROPIC_API_KEY not set")
    exit(1)

client = Anthropic(api_key=api_key)

# Try different model IDs
model_ids_to_test = [
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-20240620",
    "claude-3-5-sonnet-latest",
    "claude-3-sonnet-20240229",
    "claude-3-opus-20240229",
    "claude-3-haiku-20240307",
]

print("Testing different model IDs...\n")

for model_id in model_ids_to_test:
    print(f"Testing: {model_id}")
    try:
        response = client.messages.create(
            model=model_id,
            max_tokens=100,
            messages=[{"role": "user", "content": "Say 'hello' in JSON format: {\"message\": \"hello\"}"}]
        )
        print(f"  ✓ SUCCESS! Model {model_id} works!")
        print(f"  Response: {response.content[0].text}\n")
        break
    except Exception as e:
        print(f"  ✗ Failed: {e}\n")

print("\nIf a model worked above, use that model ID in debate.py")
