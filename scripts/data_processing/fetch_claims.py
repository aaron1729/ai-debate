#!/usr/bin/env python3
"""
Fetch claims from Google Fact Check Tools API.

This script fetches recent claims from the last week to use as test data
for the debate system. We'll compare the debate verdicts with the fact-check
ratings to evaluate system performance and biases.
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API key for Fact Check Tools API (service accounts are not supported for claims:search)
API_KEY = os.getenv('GOOGLE_API_KEY')

BASE_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

def fetch_claims(max_age_days=7, page_size=10, query='the', language_code='en'):
    """
    Fetch claims from Google Fact Check API.

    Note: This API uses API key authentication (not service account).
    Service accounts are only for pages.* write endpoints.

    Args:
        max_age_days: Maximum age of claims in days (default: 7)
        page_size: Number of results per page (default: 10, max ~20)
        query: Search query string (required, default: 'the' for broad results)
        language_code: Language code (default: 'en' for English)

    Returns:
        List of claim objects
    """
    if not API_KEY:
        raise RuntimeError(
            "GOOGLE_API_KEY not found in .env file. "
            "Note: This API requires an API key, not a service account."
        )

    all_claims = []
    next_page_token = None

    print(f"Fetching claims from the last {max_age_days} days (query: '{query}', language: {language_code})...")
    print("Using API key authentication")

    while True:
        # Build request parameters - API key auth only
        params = {
            'key': API_KEY,
            'query': query,                  # Required (or reviewPublisherSiteFilter)
            'languageCode': language_code,   # Recommended for clean results
            'pageSize': page_size,           # Keep at 10-20, not 100
            'maxAgeDays': max_age_days,
        }

        if next_page_token:
            params['pageToken'] = next_page_token

        # Make request
        try:
            response = requests.get(BASE_URL, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching claims: {e}")
            if hasattr(response, 'text') and response.text:
                print(f"Response: {response.text}")
            break

        # Extract claims
        claims = data.get('claims', [])
        if not claims:
            print("No more claims found.")
            break

        all_claims.extend(claims)
        print(f"Fetched {len(claims)} claims (total: {len(all_claims)})")

        # Check for next page
        next_page_token = data.get('nextPageToken')
        if not next_page_token:
            print("Reached end of results.")
            break

    return all_claims

def save_claims(claims, filename='claims_data.json'):
    """Save claims to JSON file with metadata."""
    output = {
        'fetched_at': datetime.now().isoformat(),
        'count': len(claims),
        'claims': claims
    }

    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved {len(claims)} claims to {filename}")

def print_summary(claims):
    """Print summary statistics about the fetched claims."""
    print(f"\n{'='*60}")
    print(f"SUMMARY: {len(claims)} claims fetched")
    print(f"{'='*60}\n")

    if not claims:
        return

    # Sample a few claims
    print("Sample claims:")
    for i, claim in enumerate(claims[:5]):
        text = claim.get('text', 'N/A')
        claimant = claim.get('claimant', 'Unknown')

        # Get first review if available
        reviews = claim.get('claimReview', [])
        rating = 'No review'
        publisher = 'Unknown'
        if reviews:
            rating = reviews[0].get('textualRating', 'N/A')
            publisher = reviews[0].get('publisher', {}).get('name', 'Unknown')

        print(f"\n{i+1}. Claim: {text[:100]}...")
        print(f"   Claimant: {claimant}")
        print(f"   Rating: {rating} (by {publisher})")

    # Count ratings
    print(f"\n{'='*60}")
    print("Rating distribution:")
    print(f"{'='*60}")

    ratings = {}
    for claim in claims:
        reviews = claim.get('claimReview', [])
        for review in reviews:
            rating = review.get('textualRating', 'Unknown')
            ratings[rating] = ratings.get(rating, 0) + 1

    for rating, count in sorted(ratings.items(), key=lambda x: x[1], reverse=True):
        print(f"  {rating}: {count}")

if __name__ == '__main__':
    # Fetch claims from last 30 days to get more data
    # Use broad query to get diverse results
    claims = fetch_claims(max_age_days=30, page_size=10, query='the', language_code='en')

    if claims:
        # Print summary
        print_summary(claims)

        # Save to file in the Google Fact Check raw data directory
        save_claims(claims, filename='data/google-fact-check/raw/claims_data.json')
    else:
        print("No claims fetched. Check API key and try again.")
