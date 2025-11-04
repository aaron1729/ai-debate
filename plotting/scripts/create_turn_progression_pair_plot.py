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

def create_turn_progression_pair_plot(claim, debater1, debater2, judge_model, output_filename):
    """
    Create a paired plot showing judge scores for two debate orientations.

    Parameters:
    - claim: The debate claim text
    - debater1: First debater (alphabetically earlier)
    - debater2: Second debater (alphabetically later)
    - judge_model: Model judging
    - output_filename: Where to save the plot

    Creates two subplots:
    - Left: debater1 as Pro, debater2 as Con
    - Right: debater1 as Con, debater2 as Pro
    """
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'experiments.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query for first orientation (debater1 as Pro)
    cursor.execute('''
        SELECT turns, judge_score
        FROM experiments
        WHERE claim = ? AND pro_model = ? AND con_model = ? AND judge_model = ?
        AND judge_score IS NOT NULL
        ORDER BY turns
    ''', (claim, debater1, debater2, judge_model))

    results1 = cursor.fetchall()

    # Query for second orientation (debater2 as Pro)
    cursor.execute('''
        SELECT turns, judge_score
        FROM experiments
        WHERE claim = ? AND pro_model = ? AND con_model = ? AND judge_model = ?
        AND judge_score IS NOT NULL
        ORDER BY turns
    ''', (claim, debater2, debater1, judge_model))

    results2 = cursor.fetchall()

    conn.close()

    if not results1 or not results2:
        print(f'Missing data for pair:')
        print(f'  Claim: {claim[:60]}...')
        print(f'  Debaters: {debater1} vs {debater2}, Judge: {judge_model}')
        print(f'  Found: {len(results1)} for orientation 1, {len(results2)} for orientation 2')
        return

    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.subplots_adjust(top=0.85, wspace=0.3)

    # Main title
    fig.suptitle(f'{claim}', fontsize=12, fontweight='bold', y=0.98)

    # Get labels and colors
    judge_label = MODEL_LABELS.get(judge_model, judge_model)
    debater1_label = MODEL_LABELS.get(debater1, debater1)
    debater2_label = MODEL_LABELS.get(debater2, debater2)
    color = MODEL_COLORS.get(judge_model, '#666666')

    # Plot 1: debater1 as Pro, debater2 as Con
    turns1 = [r[0] for r in results1]
    scores1 = [r[1] for r in results1]

    ax1.plot(turns1, scores1, 'o-', color=color, linewidth=2.5, markersize=8, alpha=0.8)
    ax1.set_xlabel('Turns', fontsize=10)
    ax1.set_ylabel('Score', fontsize=10)
    ax1.set_xticks([1, 2, 4, 6])
    ax1.set_ylim(0, 10)
    ax1.grid(True, alpha=0.3)
    ax1.text(0.5, 1, 'Contradicted', fontsize=9, alpha=0.7, style='italic',
            color=CON_COLOR, fontweight='bold')
    ax1.text(0.5, 9, 'Supported', fontsize=9, alpha=0.7, style='italic',
            color=PRO_COLOR, fontweight='bold')
    ax1.set_title(f'{debater1_label} (Pro) vs {debater2_label} (Con)', fontsize=10, pad=8)

    # Plot 2: debater2 as Pro, debater1 as Con
    turns2 = [r[0] for r in results2]
    scores2 = [r[1] for r in results2]

    ax2.plot(turns2, scores2, 'o-', color=color, linewidth=2.5, markersize=8, alpha=0.8)
    ax2.set_xlabel('Turns', fontsize=10)
    ax2.set_ylabel('Score', fontsize=10)
    ax2.set_xticks([1, 2, 4, 6])
    ax2.set_ylim(0, 10)
    ax2.grid(True, alpha=0.3)
    ax2.text(0.5, 1, 'Contradicted', fontsize=9, alpha=0.7, style='italic',
            color=CON_COLOR, fontweight='bold')
    ax2.text(0.5, 9, 'Supported', fontsize=9, alpha=0.7, style='italic',
            color=PRO_COLOR, fontweight='bold')
    ax2.set_title(f'{debater1_label} (Con) vs {debater2_label} (Pro)', fontsize=10, pad=8)

    # Subtitle with judge info
    fig.text(0.5, 0.91, f'{judge_label} judging', fontsize=10, ha='center', color='#555555')

    plt.savefig(output_filename, dpi=150, bbox_inches='tight')
    print(f'Saved to {output_filename}')

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 6:
        # Called with arguments: claim debater1 debater2 judge_model output_filename
        create_turn_progression_pair_plot(
            claim=sys.argv[1],
            debater1=sys.argv[2],
            debater2=sys.argv[3],
            judge_model=sys.argv[4],
            output_filename=sys.argv[5]
        )
    else:
        # Example usage
        create_turn_progression_pair_plot(
            claim='Higher taxes on the wealthy always reduce economic growth.',
            debater1='claude-sonnet-4-5-20250929',
            debater2='grok-3',
            judge_model='gpt-4-turbo-preview',
            output_filename='test_pair.png'
        )
