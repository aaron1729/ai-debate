#!/usr/bin/env python3
"""Create judge-judge agreement scatterplots."""

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

def create_judge_judge_agreement_plot(judge1_id, judge2_id, output_filename, full_debate_only=False):
    """Create a scatterplot showing agreement between two judges.

    Args:
        judge1_id: First judge model identifier (will be x-axis)
        judge2_id: Second judge model identifier (will be y-axis)
        output_filename: Path to save the plot
        full_debate_only: If True, only include judgments at turn 6
    """

    # Connect to database
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'experiments.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    judge1_label = MODEL_LABELS.get(judge1_id, judge1_id)
    judge2_label = MODEL_LABELS.get(judge2_id, judge2_id)

    # Add turn filter if needed
    turn_filter = "AND j1.turns_considered = 6 AND j2.turns_considered = 6" if full_debate_only else ""

    # Query: Get pairs of judgments on same experiment and turn
    # Exclude None scores
    cursor.execute(f'''
        SELECT j1.score, j2.score
        FROM judgments j1
        JOIN judgments j2
          ON j1.experiment_id = j2.experiment_id
          AND j1.turns_considered = j2.turns_considered
        WHERE j1.judge_model = ?
        AND j2.judge_model = ?
        AND j1.score IS NOT NULL
        AND j2.score IS NOT NULL
        {turn_filter}
    ''', (judge1_id, judge2_id))

    pairs = cursor.fetchall()
    conn.close()

    if not pairs:
        print(f"Warning: No matching judgments found for {judge1_label} and {judge2_label}")
        return

    judge1_scores = [p[0] for p in pairs]
    judge2_scores = [p[1] for p in pairs]

    # Create scatterplot
    fig, ax = plt.subplots(figsize=(10, 10))

    # Add jitter to avoid overplotting
    jitter_amount = 0.1
    judge1_jittered = [s + np.random.uniform(-jitter_amount, jitter_amount) for s in judge1_scores]
    judge2_jittered = [s + np.random.uniform(-jitter_amount, jitter_amount) for s in judge2_scores]

    ax.scatter(judge1_jittered, judge2_jittered, alpha=0.3, s=50, color='#2424bf', edgecolors='black', linewidth=0.5)

    # Add diagonal line (perfect agreement)
    ax.plot([0, 10], [0, 10], 'r--', linewidth=2, alpha=0.5, label='Perfect Agreement')

    # Add grid
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-0.5, 10.5)
    ax.set_ylim(-0.5, 10.5)
    ax.set_xticks(range(0, 11))
    ax.set_yticks(range(0, 11))
    ax.set_aspect('equal')

    # Labels
    title_suffix = ' (Full Debates Only)' if full_debate_only else ''
    ax.set_xlabel(f'{judge1_label} Score', fontsize=12, fontweight='bold')
    ax.set_ylabel(f'{judge2_label} Score', fontsize=12, fontweight='bold')
    ax.set_title(f'{judge1_label} vs {judge2_label} Judge Agreement{title_suffix} (n={len(pairs)})',
                 fontsize=14, fontweight='bold')

    # Calculate correlation
    correlation = np.corrcoef(judge1_scores, judge2_scores)[0, 1]
    ax.text(0.05, 0.95, f'Correlation: {correlation:.3f}',
            transform=ax.transAxes, fontsize=11, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    ax.legend(loc='lower right', fontsize=10)

    plt.tight_layout()
    plt.savefig(output_filename, dpi=150, bbox_inches='tight')
    print(f'Saved to {output_filename}')
    plt.close()

if __name__ == '__main__':
    # Test with Claude and Gemini
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                              'plotting', 'plots', 'judge-judge-agreement-scatterplot')
    os.makedirs(output_dir, exist_ok=True)

    create_judge_judge_agreement_plot(
        'claude-sonnet-4-5-20250929',
        'gemini-2.5-flash',
        os.path.join(output_dir, 'claude-gemini-judge-judge-agreement.png')
    )
