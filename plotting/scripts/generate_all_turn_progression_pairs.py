import sqlite3
import subprocess
import os
from claim_shortnames import CLAIM_SHORTNAMES

def generate_all_turn_progression_pairs():
    """Find all paired turn progression experiments and generate plots."""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'experiments.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Find all paired experiments (8 turns total = 4 for each orientation)
    cursor.execute('''
        SELECT
            claim,
            CASE
                WHEN pro_model < con_model THEN pro_model
                ELSE con_model
            END as debater1,
            CASE
                WHEN pro_model < con_model THEN con_model
                ELSE pro_model
            END as debater2,
            judge_model,
            COUNT(*) as total_turns
        FROM experiments
        WHERE judge_score IS NOT NULL
        GROUP BY claim, debater1, debater2, judge_model
        HAVING total_turns = 8
    ''')

    pairs = cursor.fetchall()
    conn.close()

    print(f'Found {len(pairs)} paired experiment sets')

    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                              'plotting', 'plots', 'score-by-turn-pairs')
    os.makedirs(output_dir, exist_ok=True)

    script_path = os.path.join(os.path.dirname(__file__), 'create_turn_progression_pair_plot.py')

    model_map = {
        'claude-sonnet-4-5-20250929': 'claude',
        'gemini-2.5-flash': 'gemini',
        'gpt-4-turbo-preview': 'gpt4',
        'grok-3': 'grok'
    }

    generated_files = []

    for claim, debater1, debater2, judge_model, _ in pairs:
        # Get shortname
        shortname = CLAIM_SHORTNAMES.get(claim, 'unknown')

        # Model labels (short)
        debater1_short = model_map.get(debater1, debater1)
        debater2_short = model_map.get(debater2, debater2)
        judge_short = model_map.get(judge_model, judge_model)

        filename = f'{shortname}_debaters-{debater1_short}-{debater2_short}_judge-{judge_short}.png'
        output_path = os.path.join(output_dir, filename)

        print(f'Generating: {filename}')

        # Call the script
        subprocess.run([
            'python3', script_path,
            claim, debater1, debater2, judge_model, output_path
        ], check=True)

        generated_files.append({
            'claim': claim,
            'debater1': debater1,
            'debater2': debater2,
            'judge': judge_model,
            'filename': filename
        })

    print(f'\nGenerated {len(generated_files)} paired plots in {output_dir}')

    return generated_files

if __name__ == '__main__':
    generate_all_turn_progression_pairs()
