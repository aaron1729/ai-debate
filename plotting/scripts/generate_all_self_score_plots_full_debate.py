#!/usr/bin/env python3
"""Generate self-score distribution plots for all judge models (full debates only)."""

import os
import sys
from create_self_score_plot import create_self_score_plot, MODEL_LABELS

def main():
    # Get output directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    output_dir = os.path.join(project_root, 'plotting', 'plots', 'self-score-histogram')

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Generate plot for each model (full debates only - turn >= 6)
    models = [
        ('claude-sonnet-4-5-20250929', 'claude_self_scores_full_debate_only.png'),
        ('gemini-2.5-flash', 'gemini_self_scores_full_debate_only.png'),
        ('gpt-4-turbo-preview', 'gpt4_self_scores_full_debate_only.png'),
        ('grok-3', 'grok_self_scores_full_debate_only.png'),
    ]

    for model_id, filename in models:
        model_label = MODEL_LABELS.get(model_id, model_id)

        # Generate regular plot
        output_path = os.path.join(output_dir, filename)
        print(f'\nGenerating {filename} for {model_label}...')

        try:
            create_self_score_plot(model_id, output_path, full_debate_only=True)
            print(f'✓ Successfully generated {filename}')
        except Exception as e:
            print(f'✗ Error generating {filename}: {e}')
            return 1

        # Generate normalized plot
        normalized_filename = filename.replace('.png', '_normalized.png')
        normalized_output_path = os.path.join(output_dir, normalized_filename)
        print(f'Generating {normalized_filename} for {model_label}...')

        try:
            create_self_score_plot(model_id, normalized_output_path, full_debate_only=True, normalized=True)
            print(f'✓ Successfully generated {normalized_filename}')
        except Exception as e:
            print(f'✗ Error generating {normalized_filename}: {e}')
            return 1

    print('\n✓ All full-debate-only self-score plots generated successfully!')
    return 0

if __name__ == '__main__':
    sys.exit(main())
