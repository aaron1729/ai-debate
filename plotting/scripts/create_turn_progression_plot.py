import sqlite3
import matplotlib.pyplot as plt
import numpy as np
import os

# Consistent color scheme
MODEL_COLORS = {
    'claude-sonnet-4-5-20250929': '#8B5CF6',  # purple
    'gemini-2.5-flash': '#2424bf',  # blue
    'gpt-4-turbo-preview': '#F97316',  # lighter orange
    'grok-3': '#f96bf3'  # bright pink
}

MODEL_LABELS = {
    'claude-sonnet-4-5-20250929': 'Claude',
    'gemini-2.5-flash': 'Gemini',
    'gpt-4-turbo-preview': 'GPT-4',
    'grok-3': 'Grok'
}

PRO_COLOR = '#007000'  # green
CON_COLOR = '#D22222'  # red

def create_turn_progression_plot(claim, pro_model, con_model, judge_model, output_filename):
    """
    Create a plot showing how judge scores change across debate turns.

    Parameters:
    - claim: The debate claim text
    - pro_model: Model arguing Pro
    - con_model: Model arguing Con
    - judge_model: Model judging
    - output_filename: Where to save the plot
    """
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'experiments.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query for experiments matching this 4-tuple, using legacy schema
    cursor.execute('''
        SELECT turns, judge_score, id
        FROM experiments
        WHERE claim = ? AND pro_model = ? AND con_model = ? AND judge_model = ?
        AND judge_score IS NOT NULL
        ORDER BY turns
    ''', (claim, pro_model, con_model, judge_model))

    results = cursor.fetchall()

    if not results:
        print(f'No experiments found for:')
        print(f'  Claim: {claim[:60]}...')
        print(f'  Pro: {pro_model}, Con: {con_model}, Judge: {judge_model}')
        conn.close()
        return

    if len(results) != 4:
        print(f'Warning: Expected 4 turns (1,2,4,6), found {len(results)} for:')
        print(f'  Claim: {claim[:60]}...')

    turns = [r[0] for r in results]
    scores = [r[1] for r in results]

    # Create plot
    fig, ax = plt.subplots(figsize=(9, 6))

    # Get color for judge
    color = MODEL_COLORS.get(judge_model, '#666666')
    judge_label = MODEL_LABELS.get(judge_model, judge_model)

    # Plot line and points
    ax.plot(turns, scores, 'o-', color=color, linewidth=2.5, markersize=8, alpha=0.8, label=judge_label)

    # Formatting
    ax.set_xlabel('Turns', fontsize=11)
    ax.set_ylabel('Score', fontsize=11)
    ax.set_xticks([1, 2, 4, 6])
    ax.set_ylim(0, 10)
    ax.grid(True, alpha=0.3)

    # Add "Contradicted" and "Supported" labels
    ax.text(0.5, 1, 'Contradicted', fontsize=10, alpha=0.7, style='italic',
            color=CON_COLOR, fontweight='bold')
    ax.text(0.5, 9, 'Supported', fontsize=10, alpha=0.7, style='italic',
            color=PRO_COLOR, fontweight='bold')

    # Build title with debater info
    pro_label = MODEL_LABELS.get(pro_model, pro_model)
    con_label = MODEL_LABELS.get(con_model, con_model)
    pro_color = MODEL_COLORS.get(pro_model, '#666666')
    con_color = MODEL_COLORS.get(con_model, '#666666')

    # Title: Debate claim
    fig.suptitle(f'{claim}', fontsize=11, fontweight='bold', y=0.98)

    # Subtitle: Judge and debaters
    subtitle = f'{judge_label} judging: {pro_label} (Pro) vs {con_label} (Con)'
    ax.set_title(subtitle, fontsize=10, pad=10, color='#555555')

    plt.tight_layout()
    plt.savefig(output_filename, dpi=150, bbox_inches='tight')
    print(f'Saved to {output_filename}')
    conn.close()

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 6:
        # Called with arguments: claim pro_model con_model judge_model output_filename
        create_turn_progression_plot(
            claim=sys.argv[1],
            pro_model=sys.argv[2],
            con_model=sys.argv[3],
            judge_model=sys.argv[4],
            output_filename=sys.argv[5]
        )
    else:
        # Example usage
        create_turn_progression_plot(
            claim='After controlling for inflation and productivity growth, raising the federal minimum wage modestly does not consistently cause overall job losses.',
            pro_model='grok-3',
            con_model='claude-sonnet-4-5-20250929',
            judge_model='gpt-4-turbo-preview',
            output_filename='test_turn_progression.png'
        )
