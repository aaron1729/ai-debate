#!/usr/bin/env python3
"""Generate judge-judge agreement plots for all pairs."""

import os
import sys
from itertools import combinations
from create_judge_judge_agreement_plot import create_judge_judge_agreement_plot, MODEL_LABELS

def main():
    # Get output directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    output_dir = os.path.join(project_root, 'plotting', 'plots', 'judge-judge-agreement')

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # All models
    models = [
        ('claude-sonnet-4-5-20250929', 'claude'),
        ('gemini-2.5-flash', 'gemini'),
        ('gpt-4-turbo-preview', 'gpt4'),
        ('grok-3', 'grok'),
    ]

    # Generate plot for each distinct pair (alphabetically ordered)
    # Sort by the short name to ensure consistent ordering
    models_sorted = sorted(models, key=lambda x: x[1])

    for i, (judge1_id, judge1_name) in enumerate(models_sorted):
        for judge2_id, judge2_name in models_sorted[i+1:]:
            # Alphabetical ordering for filename
            filename = f'{judge1_name}-{judge2_name}-judge-judge-agreement.png'
            output_path = os.path.join(output_dir, filename)

            judge1_label = MODEL_LABELS.get(judge1_id, judge1_id)
            judge2_label = MODEL_LABELS.get(judge2_id, judge2_id)

            print(f'\nGenerating {filename}...')
            print(f'  {judge1_label} vs {judge2_label}')

            try:
                create_judge_judge_agreement_plot(judge1_id, judge2_id, output_path)
                print(f'✓ Successfully generated {filename}')
            except Exception as e:
                print(f'✗ Error generating {filename}: {e}')
                return 1

    total_pairs = len(models) * (len(models) - 1) // 2
    print(f'\n✓ All {total_pairs} judge-judge agreement plots generated successfully!')
    return 0

if __name__ == '__main__':
    sys.exit(main())
