#!/usr/bin/env python3
"""Generate new debate plots with standardized naming."""

import subprocess
import sys
import os

# Plot configurations: (experiment_ids, output_filename)
PLOTS = [
    ([243, 285, 286, 287], 'sex_work_debates_claude_gpt4.png'),
    ([257, 259, 261, 262], 'china_debates_claude_gemini.png'),
    ([255, 256, 258, 260], 'tax_debates_gpt4_grok.png'),
    ([270, 276, 283, 284], 'political_correctness_debates_claude_gemini.png'),
    ([268, 274, 278, 282], 'political_correctness_debates_claude_gpt4.png'),
    ([267, 271, 277, 281], 'political_correctness_debates_gemini_gpt4.png'),
    ([266, 272, 279, 280], 'political_correctness_debates_gemini_grok.png'),
    ([265, 269, 273, 275], 'political_correctness_debates_gpt4_grok.png'),
]

def main():
    # Get the project root (two levels up from this script)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    output_dir = os.path.join(project_root, 'plotting', 'plots', 'debate-motions')

    for exp_ids, output_file in PLOTS:
        output_path = os.path.join(output_dir, output_file)
        print(f'\nGenerating {output_file}...')

        # Create a temporary Python script to run
        exp_ids_str = ','.join(map(str, exp_ids))
        script = f'''
import sys
sys.path.insert(0, '{project_root}/plotting/scripts')
from create_debate_plot import create_debate_plot_from_ids

create_debate_plot_from_ids([{exp_ids_str}], '{output_path}')
'''

        # Run it
        result = subprocess.run(
            ['python', '-c', script],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f'✓ Successfully generated {output_file}')
        else:
            print(f'✗ Error generating {output_file}:')
            print(result.stderr)
            return 1

    print('\n✓ All plots generated successfully!')
    return 0

if __name__ == '__main__':
    sys.exit(main())
