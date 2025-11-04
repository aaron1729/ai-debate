#!/usr/bin/env python3
"""Generate judge-debater agreement plots for all combinations."""

import os
import sys
from create_judge_debater_agreement_plot import create_judge_debater_agreement_plot, MODEL_LABELS

def main():
    # Get output directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    output_dir = os.path.join(project_root, 'plotting', 'plots', 'judge-debater-agreement-histogram')

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # All models
    models = [
        ('claude-sonnet-4-5-20250929', 'claude'),
        ('gemini-2.5-flash', 'gemini'),
        ('gpt-4-turbo-preview', 'gpt4'),
        ('grok-3', 'grok'),
    ]

    # Generate plot for each judge-debater pair (including same model)
    for judge_id, judge_name in models:
        for debater_id, debater_name in models:
            # Generate regular plot
            filename = f'judge={judge_name}_debater={debater_name}_agreement.png'
            output_path = os.path.join(output_dir, filename)

            judge_label = MODEL_LABELS.get(judge_id, judge_id)
            debater_label = MODEL_LABELS.get(debater_id, debater_id)

            print(f'\nGenerating {filename}...')
            print(f'  {judge_label} judging {debater_label}')

            try:
                create_judge_debater_agreement_plot(judge_id, debater_id, output_path)
                print(f'✓ Successfully generated {filename}')
            except Exception as e:
                print(f'✗ Error generating {filename}: {e}')
                return 1

            # Generate normalized plot
            normalized_filename = f'judge={judge_name}_debater={debater_name}_agreement_normalized.png'
            normalized_output_path = os.path.join(output_dir, normalized_filename)

            print(f'Generating {normalized_filename}...')

            try:
                create_judge_debater_agreement_plot(judge_id, debater_id, normalized_output_path, normalized=True)
                print(f'✓ Successfully generated {normalized_filename}')
            except Exception as e:
                print(f'✗ Error generating {normalized_filename}: {e}')
                return 1

    print(f'\n✓ All {len(models) * len(models) * 2} judge-debater agreement plots generated successfully!')
    return 0

if __name__ == '__main__':
    sys.exit(main())
