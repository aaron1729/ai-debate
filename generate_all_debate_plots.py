#!/usr/bin/env python3
"""Generate debate plots for all three main debate motions."""

import subprocess
import sys

# The three debate motions we ran the full suite on
MOTIONS = [
    ('%political correctness%', 'political_correctness_debates.png'),
    ('%anti-Zionism is anti-Semitism%', 'anti_zionism_debates.png'),
    ('%United States started the new Cold War%', 'cold_war_debates.png'),
]

def main():
    for pattern, output_file in MOTIONS:
        print(f'\nGenerating {output_file}...')

        # Create a temporary Python script to run
        script = f'''
import sys
sys.path.insert(0, '/Users/aaron/git/ai-debate')
from create_debate_plot import create_debate_plot

create_debate_plot('{pattern}', '{output_file}')
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
