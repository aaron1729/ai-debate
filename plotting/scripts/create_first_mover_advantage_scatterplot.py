#!/usr/bin/env python3
"""Create scatterplots showing judge scores for paired debates (pro first vs con first)."""

import sqlite3
import matplotlib.pyplot as plt
import numpy as np
import os
from collections import defaultdict

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

def get_paired_debate_scores():
    """Get scores for paired debates (same claim, different turn order).

    Returns:
        dict: {judge_model: [(pro_first_score, con_first_score), ...]}
    """
    # Connect to database
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                          'data', 'experiments.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Find pairs of experiments with same claim but different pro_went_first values
    # Group by claim, pro_model, con_model, judge_model to find exact matches
    cursor.execute('''
        SELECT
            e1.id as exp1_id,
            e2.id as exp2_id,
            e1.claim,
            e1.pro_went_first as e1_pro_first,
            e2.pro_went_first as e2_pro_first
        FROM experiments e1
        JOIN experiments e2
            ON e1.claim = e2.claim
            AND e1.pro_model = e2.pro_model
            AND e1.con_model = e2.con_model
            AND e1.pro_went_first != e2.pro_went_first
            AND e1.id < e2.id
        WHERE e1.claim IS NOT NULL
        AND e2.claim IS NOT NULL
    ''')

    pairs = cursor.fetchall()

    if not pairs:
        print("No paired debates found")
        conn.close()
        return {}

    print(f"Found {len(pairs)} paired debates")

    # For each pair, get all judgments
    judge_scores = defaultdict(list)

    for exp1_id, exp2_id, claim, e1_pro_first, e2_pro_first in pairs:
        # Determine which experiment is pro_first and which is con_first
        if e1_pro_first == 1:
            pro_first_exp = exp1_id
            con_first_exp = exp2_id
        else:
            pro_first_exp = exp2_id
            con_first_exp = exp1_id

        # Get judgments for both experiments
        cursor.execute('''
            SELECT judge_model, turns_considered, score
            FROM judgments
            WHERE experiment_id = ?
            AND score IS NOT NULL
            ORDER BY turns_considered
        ''', (pro_first_exp,))

        pro_first_judgments = defaultdict(dict)
        for judge_model, turn, score in cursor.fetchall():
            pro_first_judgments[judge_model][turn] = score

        cursor.execute('''
            SELECT judge_model, turns_considered, score
            FROM judgments
            WHERE experiment_id = ?
            AND score IS NOT NULL
            ORDER BY turns_considered
        ''', (con_first_exp,))

        con_first_judgments = defaultdict(dict)
        for judge_model, turn, score in cursor.fetchall():
            con_first_judgments[judge_model][turn] = score

        # Match up judgments by judge and turn
        all_judges = set(pro_first_judgments.keys()) & set(con_first_judgments.keys())

        for judge_model in all_judges:
            pro_turns = pro_first_judgments[judge_model]
            con_turns = con_first_judgments[judge_model]

            # Find common turns judged by both
            common_turns = set(pro_turns.keys()) & set(con_turns.keys())

            for turn in common_turns:
                pro_score = pro_turns[turn]
                con_score = con_turns[turn]
                judge_scores[judge_model].append((pro_score, con_score))

    conn.close()

    # Print statistics
    for judge_model, scores in judge_scores.items():
        label = MODEL_LABELS.get(judge_model, judge_model)
        print(f"{label}: {len(scores)} paired scores")

    return judge_scores

def create_first_mover_advantage_scatterplot(output_filename):
    """Create scatterplot showing scores for pro-first vs con-first debates.

    Args:
        output_filename: Path to save the plot
    """
    judge_scores = get_paired_debate_scores()

    if not judge_scores:
        print("No paired scores to plot")
        return

    # Sort judges alphabetically by label
    judges_sorted = sorted(judge_scores.keys(),
                          key=lambda x: MODEL_LABELS.get(x, x))

    # Create aggregate (all judges pooled)
    all_scores = []
    for scores in judge_scores.values():
        all_scores.extend(scores)

    # Create figure with 1x5 subplots
    fig, axes = plt.subplots(1, 5, figsize=(25, 5))

    # Prepare data
    plot_data = [
        ('Aggregate', all_scores, '#666666'),  # gray for aggregate
    ]

    for judge_model in judges_sorted:
        label = MODEL_LABELS.get(judge_model, judge_model)
        color = MODEL_COLORS.get(judge_model, '#000000')
        plot_data.append((label, judge_scores[judge_model], color))

    # Plot each subplot
    for col, (label, scores, color) in enumerate(plot_data):
        ax = axes[col]

        if scores:
            pro_first_scores = [s[0] for s in scores]
            con_first_scores = [s[1] for s in scores]

            # Calculate second-mover advantage (con_first - pro_first)
            second_mover_advantages = [con - pro for pro, con in zip(pro_first_scores, con_first_scores)]
            avg_advantage = np.mean(second_mover_advantages)
            median_advantage = np.median(second_mover_advantages)

            # Add jitter to avoid overplotting
            jitter_amount = 0.1
            pro_jittered = [s + np.random.uniform(-jitter_amount, jitter_amount) for s in pro_first_scores]
            con_jittered = [s + np.random.uniform(-jitter_amount, jitter_amount) for s in con_first_scores]

            ax.scatter(pro_jittered, con_jittered, alpha=0.5, s=50,
                      color=color, edgecolors='black', linewidth=0.5)

            # Add diagonal line (no advantage)
            ax.plot([0, 10], [0, 10], 'r--', linewidth=2, alpha=0.5, label='No Advantage')

            # Add second-mover advantage text
            advantage_text = f'Second-mover advantage:\naverage {avg_advantage:+.1f} points, median {median_advantage:+.1f} points'
            ax.text(0.02, 0.98, advantage_text, transform=ax.transAxes,
                   fontsize=9, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8, edgecolor='gray'))

        # Formatting
        ax.set_xlim(-0.5, 10.5)
        ax.set_ylim(-0.5, 10.5)
        ax.set_xticks(range(0, 11))
        ax.set_yticks(range(0, 11))
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.set_title(f'{label}\n(n={len(scores)})', fontsize=12, fontweight='bold')
        ax.set_xlabel('Score (Pro First)', fontsize=11)
        if col == 0:
            ax.set_ylabel('Score (Con First)', fontsize=11)
        ax.legend(loc='lower right', fontsize=9)

    # Overall title
    fig.suptitle('Judge Scores: Pro First vs Con First (Paired Debates)',
                fontsize=14, fontweight='bold', y=1.02)

    plt.tight_layout()
    plt.savefig(output_filename, dpi=150, bbox_inches='tight')
    print(f'Saved to {output_filename}')
    plt.close()

if __name__ == '__main__':
    # Create output directory
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                              'plotting', 'plots', 'first-mover-advantage-scatterplot')
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, 'first-mover-advantage.png')
    create_first_mover_advantage_scatterplot(output_path)
