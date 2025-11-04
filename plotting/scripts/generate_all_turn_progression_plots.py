import sqlite3
import subprocess
import os
import re

def sanitize_filename(text):
    """Convert text to a safe filename."""
    # Take first 50 chars
    text = text[:50]
    # Replace spaces and special chars with underscores
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '_', text)
    text = text.strip('_').lower()
    return text

def generate_all_turn_progression_plots():
    """Find all complete turn progression experiments and generate plots."""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'experiments.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Find all 4-tuples with exactly turns 1,2,4,6 and non-null scores
    cursor.execute('''
        SELECT claim, pro_model, con_model, judge_model, COUNT(*) as num_turns, GROUP_CONCAT(turns) as turn_list
        FROM experiments
        WHERE judge_score IS NOT NULL
        GROUP BY claim, pro_model, con_model, judge_model
        HAVING COUNT(*) = 4 AND turn_list = '1,2,4,6'
    ''')

    experiment_sets = cursor.fetchall()
    conn.close()

    print(f'Found {len(experiment_sets)} complete experiment sets')

    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                              'plotting', 'plots', 'score-by-turn')
    os.makedirs(output_dir, exist_ok=True)

    script_path = os.path.join(os.path.dirname(__file__), 'create_turn_progression_plot.py')

    for claim, pro_model, con_model, judge_model, _, _ in experiment_sets:
        # Create filename
        claim_part = sanitize_filename(claim)

        # Model labels (short)
        model_map = {
            'claude-sonnet-4-5-20250929': 'claude',
            'gemini-2.5-flash': 'gemini',
            'gpt-4-turbo-preview': 'gpt4',
            'grok-3': 'grok'
        }
        pro_short = model_map.get(pro_model, pro_model)
        con_short = model_map.get(con_model, con_model)
        judge_short = model_map.get(judge_model, judge_model)

        filename = f'{claim_part}__pro_{pro_short}__con_{con_short}__judge_{judge_short}.png'
        output_path = os.path.join(output_dir, filename)

        print(f'Generating: {filename}')

        # Call the script
        subprocess.run([
            'python3', script_path,
            claim, pro_model, con_model, judge_model, output_path
        ], check=True)

    print(f'\nGenerated {len(experiment_sets)} plots in {output_dir}')

if __name__ == '__main__':
    generate_all_turn_progression_plots()
