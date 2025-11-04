#!/usr/bin/env python3
"""Create judge-debater agreement plots showing score distributions."""

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

def create_judge_debater_agreement_plot(judge_id, debater_id, output_filename, normalized=False):
    """Create a 2-subplot histogram showing score distributions for a judge-debater pair.

    Args:
        judge_id: The judge model identifier
        debater_id: The debater model identifier
        output_filename: Path to save the plot
        normalized: If True, normalize histograms to show density/percentage instead of counts
    """

    # Connect to database
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'experiments.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    judge_label = MODEL_LABELS.get(judge_id, judge_id)
    debater_label = MODEL_LABELS.get(debater_id, debater_id)
    judge_color = MODEL_COLORS.get(judge_id, '#666666')

    # Query 1: Scores when debater is Pro
    cursor.execute('''
        SELECT j.score
        FROM judgments j
        JOIN experiments e ON j.experiment_id = e.id
        WHERE j.judge_model = ?
        AND e.pro_model = ?
        AND j.score IS NOT NULL
    ''', (judge_id, debater_id))
    pro_scores = [row[0] for row in cursor.fetchall()]

    # Query 2: Scores when debater is Con
    cursor.execute('''
        SELECT j.score
        FROM judgments j
        JOIN experiments e ON j.experiment_id = e.id
        WHERE j.judge_model = ?
        AND e.con_model = ?
        AND j.score IS NOT NULL
    ''', (judge_id, debater_id))
    con_scores = [row[0] for row in cursor.fetchall()]

    conn.close()

    # Create figure with 2 vertically aligned subplots
    fig, axes = plt.subplots(2, 1, figsize=(10, 8))
    fig.suptitle(f'{judge_label} Judging {debater_label}', fontsize=14, fontweight='bold')

    # Bins for integers 0-10
    bins = np.arange(0, 12) - 0.5  # Centers bins on integers

    # Determine histogram parameters based on normalization
    if normalized:
        density = True
        ylabel = 'Density'
        # Calculate max density across both distributions for shared y-axis
        all_densities = []
        for scores in [pro_scores, con_scores]:
            if scores:
                counts, _ = np.histogram(scores, bins=bins, density=True)
                all_densities.extend(counts)
        max_density = max(all_densities) if all_densities else 0.1
        y_max = max_density * 1.1  # Add 10% headroom
    else:
        density = False
        ylabel = 'Count'
        # Calculate max count across both distributions for shared y-axis
        all_counts = []
        for scores in [pro_scores, con_scores]:
            if scores:
                counts, _ = np.histogram(scores, bins=bins)
                all_counts.extend(counts)
        max_count = max(all_counts) if all_counts else 10
        y_max = max_count * 1.1  # Add 10% headroom

    # Plot 1: Debater arguing Pro
    axes[0].hist(pro_scores, bins=bins, color=judge_color, alpha=0.7, edgecolor='black', density=density)
    axes[0].set_ylabel(ylabel, fontsize=11)
    axes[0].set_title(f'{debater_label} Arguing Pro (n={len(pro_scores)})', fontsize=12)
    axes[0].set_ylim(0, y_max)
    axes[0].grid(True, alpha=0.3, axis='y')
    axes[0].set_xticks(range(0, 11))

    # Plot 2: Debater arguing Con
    axes[1].hist(con_scores, bins=bins, color=judge_color, alpha=0.7, edgecolor='black', density=density)
    axes[1].set_xlabel('Score', fontsize=11)
    axes[1].set_ylabel(ylabel, fontsize=11)
    axes[1].set_title(f'{debater_label} Arguing Con (n={len(con_scores)})', fontsize=12)
    axes[1].set_ylim(0, y_max)
    axes[1].grid(True, alpha=0.3, axis='y')
    axes[1].set_xticks(range(0, 11))

    # Add note
    note_text = ('Higher scores favor Pro position (claim is true). Lower scores favor Con position (claim is false).')
    fig.text(0.5, 0.02, note_text, fontsize=9, ha='center', va='bottom', style='italic', color='#666666')

    plt.tight_layout()
    plt.savefig(output_filename, dpi=150, bbox_inches='tight')
    print(f'Saved to {output_filename}')
    plt.close()

if __name__ == '__main__':
    # Test with Claude judging Grok
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                              'plotting', 'plots', 'judge-debater-agreement-histogram')
    os.makedirs(output_dir, exist_ok=True)

    create_judge_debater_agreement_plot(
        'claude-sonnet-4-5-20250929',
        'grok-3',
        os.path.join(output_dir, 'judge=claude_debater=grok_agreement.png')
    )
