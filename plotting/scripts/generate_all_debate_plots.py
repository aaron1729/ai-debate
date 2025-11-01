#!/usr/bin/env python3
"""Generate debate plots for all fully-judged debate motions."""

import subprocess
import sys
import os

# All 8 debate motions that have been fully run (4 debates each) and judged by all 4 models
MOTIONS = [
    ('%religion was a force for good%', 'religion_debates.png'),
    ('%state surveillance was a legitimate defense%', 'surveillance_debates.png'),
    ('%political correctness%', 'political_correctness_debates.png'),
    ('%capitalist system was broken%', 'capitalism_debates.png'),
    ('%anti-Zionism is anti-Semitism%', 'antizionism_debates.png'),
    ('%United States started the new Cold War%', 'cold_war_debates.png'),
    ('%AI research and development poses an existential threat%', 'ai_threat_debates.png'),
    ('%preferable to get sick in the United States than in Canada%', 'healthcare_debates.png'),
]

def main():
    # Get the project root (two levels up from this script)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    output_dir = os.path.join(project_root, 'plotting', 'plots', 'debate-motions')

    for pattern, output_file in MOTIONS:
        output_path = os.path.join(output_dir, output_file)
        print(f'\nGenerating {output_file}...')

        # Create a temporary Python script to run
        script = f'''
import sys
sys.path.insert(0, '{project_root}/plotting/scripts')
from create_debate_plot import create_debate_plot

create_debate_plot('{pattern}', '{output_path}')
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
