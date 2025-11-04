#!/usr/bin/env python3
"""Create self-score distribution plots for judge models."""

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

def create_self_score_plot(model_id, output_filename, full_debate_only=False, normalized=False):
    """Create a 3-subplot histogram showing score distributions for a model.

    Args:
        model_id: The model identifier
        output_filename: Path to save the plot
        full_debate_only: If True, only include judgments after turn 6
        normalized: If True, normalize histograms to show density/percentage instead of counts
    """

    # Connect to database
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'experiments.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    model_label = MODEL_LABELS.get(model_id, model_id)
    model_color = MODEL_COLORS.get(model_id, '#666666')

    # Add turn filter if needed
    turn_filter = "AND j.turns_considered >= 6" if full_debate_only else ""

    # Query 1: All scores given by this model (excluding None)
    cursor.execute(f'''
        SELECT score
        FROM judgments j
        WHERE judge_model = ? AND score IS NOT NULL
        {turn_filter}
    ''', (model_id,))
    all_scores = [row[0] for row in cursor.fetchall()]

    # Query 2: Scores given to itself arguing Pro
    cursor.execute(f'''
        SELECT j.score
        FROM judgments j
        JOIN experiments e ON j.experiment_id = e.id
        WHERE j.judge_model = ?
        AND e.pro_model = ?
        AND j.score IS NOT NULL
        {turn_filter}
    ''', (model_id, model_id))
    pro_scores = [row[0] for row in cursor.fetchall()]

    # Query 3: Scores given to itself arguing Con
    cursor.execute(f'''
        SELECT j.score
        FROM judgments j
        JOIN experiments e ON j.experiment_id = e.id
        WHERE j.judge_model = ?
        AND e.con_model = ?
        AND j.score IS NOT NULL
        {turn_filter}
    ''', (model_id, model_id))
    con_scores = [row[0] for row in cursor.fetchall()]

    conn.close()

    # Create figure with 3 vertically aligned subplots
    fig, axes = plt.subplots(3, 1, figsize=(10, 12))
    title_suffix = ' (Full Debates Only)' if full_debate_only else ''
    fig.suptitle(f'{model_label} Score Distributions{title_suffix}', fontsize=14, fontweight='bold')

    # Bins for integers 0-10
    bins = np.arange(0, 12) - 0.5  # Centers bins on integers

    # Determine histogram parameters based on normalization
    if normalized:
        density = True
        ylabel = 'Density'
        # Calculate max density across all three distributions for shared y-axis
        all_densities = []
        for scores in [all_scores, pro_scores, con_scores]:
            if scores:
                counts, _ = np.histogram(scores, bins=bins, density=True)
                all_densities.extend(counts)
        max_density = max(all_densities) if all_densities else 0.1
        y_max = max_density * 1.1  # Add 10% headroom
    else:
        density = False
        ylabel = 'Count'
        # Calculate max count across all three distributions for shared y-axis
        all_counts = []
        for scores in [all_scores, pro_scores, con_scores]:
            if scores:
                counts, _ = np.histogram(scores, bins=bins)
                all_counts.extend(counts)
        max_count = max(all_counts) if all_counts else 10
        y_max = max_count * 1.1  # Add 10% headroom

    # Plot 1: All scores
    axes[0].hist(all_scores, bins=bins, color=model_color, alpha=0.7, edgecolor='black', density=density)
    axes[0].set_ylabel(ylabel, fontsize=11)
    axes[0].set_title(f'All Scores Given by {model_label} (n={len(all_scores)})', fontsize=12)
    axes[0].set_ylim(0, y_max)
    axes[0].grid(True, alpha=0.3, axis='y')
    axes[0].set_xticks(range(0, 11))

    # Plot 2: Scores when judging itself as Pro
    axes[1].hist(pro_scores, bins=bins, color=model_color, alpha=0.7, edgecolor='black', density=density)
    axes[1].set_ylabel(ylabel, fontsize=11)
    axes[1].set_title(f'Scores Given to Itself Arguing Pro (n={len(pro_scores)})', fontsize=12)
    axes[1].set_ylim(0, y_max)
    axes[1].grid(True, alpha=0.3, axis='y')
    axes[1].set_xticks(range(0, 11))

    # Plot 3: Scores when judging itself as Con
    axes[2].hist(con_scores, bins=bins, color=model_color, alpha=0.7, edgecolor='black', density=density)
    axes[2].set_xlabel('Score', fontsize=11)
    axes[2].set_ylabel(ylabel, fontsize=11)
    axes[2].set_title(f'Scores Given to Itself Arguing Con (n={len(con_scores)})', fontsize=12)
    axes[2].set_ylim(0, y_max)
    axes[2].grid(True, alpha=0.3, axis='y')
    axes[2].set_xticks(range(0, 11))

    plt.tight_layout()
    plt.savefig(output_filename, dpi=150, bbox_inches='tight')
    print(f'Saved to {output_filename}')
    plt.close()

if __name__ == '__main__':
    # Test with Gemini
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                              'plotting', 'plots', 'self-score-histogram')
    os.makedirs(output_dir, exist_ok=True)

    create_self_score_plot('gemini-2.5-flash', os.path.join(output_dir, 'gemini_self_scores.png'))
