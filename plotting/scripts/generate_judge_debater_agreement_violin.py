#!/usr/bin/env python3
"""Generate judge-debater agreement violin plot."""

import os
import sys
from create_judge_debater_agreement_violin import create_judge_debater_agreement_violin

def main():
    # Get output directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    output_dir = os.path.join(project_root, 'plotting', 'plots', 'judge-debater-agreement-violin')

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, 'judge_debater_agreement_violin_grid.png')

    print('Generating judge-debater agreement violin plot...')

    try:
        create_judge_debater_agreement_violin(output_path)
        print('✓ Successfully generated violin plot')
    except Exception as e:
        print(f'✗ Error generating violin plot: {e}')
        import traceback
        traceback.print_exc()
        return 1

    print(f'\n✓ Violin plot generated successfully!')
    return 0

if __name__ == '__main__':
    sys.exit(main())
