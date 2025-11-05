#!/usr/bin/env python3
"""Create heatmaps showing judge score changes from turn to turn."""

import sqlite3
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
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

def get_score_changes_by_turn():
    """Get score changes for debates where all 6 turns were judged.

    Returns:
        dict: {judge_model: {turn_transition: [list of score differences]}}
              where turn_transition is 1 (for 1→2), 2 (for 2→3), etc.
    """
    # Connect to database
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                          'data', 'experiments.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # First, find experiments where at least one judge has judged all 6 turns
    cursor.execute('''
        SELECT DISTINCT experiment_id
        FROM judgments
        WHERE score IS NOT NULL
        GROUP BY experiment_id, judge_model
        HAVING COUNT(DISTINCT turns_considered) = 6
    ''')

    valid_experiments = [row[0] for row in cursor.fetchall()]

    if not valid_experiments:
        print("No experiments found with all 6 turns judged")
        conn.close()
        return {}

    print(f"Found {len(valid_experiments)} experiments with all 6 turns judged by at least one judge")

    # Get all judgments for these experiments, ordered by turn
    placeholders = ','.join('?' * len(valid_experiments))
    cursor.execute(f'''
        SELECT experiment_id, judge_model, turns_considered, score
        FROM judgments
        WHERE experiment_id IN ({placeholders})
        AND score IS NOT NULL
        ORDER BY experiment_id, judge_model, turns_considered
    ''', valid_experiments)

    # Organize by experiment and judge
    judgments_by_exp_judge = defaultdict(lambda: defaultdict(dict))
    for exp_id, judge_model, turn, score in cursor.fetchall():
        judgments_by_exp_judge[exp_id][judge_model][turn] = score

    conn.close()

    # Calculate score changes for each judge, organized by turn transition
    score_changes = defaultdict(lambda: defaultdict(list))

    for exp_id, judges in judgments_by_exp_judge.items():
        for judge_model, turns in judges.items():
            # Only process if this judge has all 6 turns for this experiment
            if len(turns) == 6 and all(t in turns for t in range(1, 7)):
                # Calculate differences for turns 1→2, 2→3, ..., 5→6
                for turn_transition in range(1, 6):  # 1, 2, 3, 4, 5
                    diff = turns[turn_transition + 1] - turns[turn_transition]
                    score_changes[judge_model][turn_transition].append(diff)

    return score_changes

def create_score_change_heatmap(output_filename, exclude_zeros=False):
    """Create heatmap showing score changes for all judges across turns.

    Args:
        output_filename: Path to save the plot
        exclude_zeros: If True, filter out all zero changes
    """
    score_changes_by_turn = get_score_changes_by_turn()

    if not score_changes_by_turn:
        print("No score changes to plot")
        return

    # Sort judges alphabetically by label
    judges_sorted = sorted(score_changes_by_turn.keys(),
                          key=lambda x: MODEL_LABELS.get(x, x))

    # Create aggregate (all judges pooled) by turn
    all_changes_by_turn = defaultdict(list)
    for judge_changes in score_changes_by_turn.values():
        for turn_transition, changes in judge_changes.items():
            if exclude_zeros:
                # Filter out zeros
                filtered_changes = [c for c in changes if c != 0]
                all_changes_by_turn[turn_transition].extend(filtered_changes)
            else:
                all_changes_by_turn[turn_transition].extend(changes)

    # Create figure with 2x5 subplots
    fig, axes = plt.subplots(2, 5, figsize=(20, 10))

    # Turn transitions: 1→2, 2→3, 3→4, 4→5, 5→6
    turn_transitions = [1, 2, 3, 4, 5]
    turn_labels = ['1→2', '2→3', '3→4', '4→5', '5→6']

    # Prepare data for heatmaps
    plot_data = [
        ('Aggregate', all_changes_by_turn, '#666666'),  # gray for aggregate
    ]

    for judge_model in judges_sorted:
        label = MODEL_LABELS.get(judge_model, judge_model)
        color = MODEL_COLORS.get(judge_model, '#000000')
        judge_changes = score_changes_by_turn[judge_model]
        if exclude_zeros:
            # Filter out zeros for this judge
            filtered_judge_changes = defaultdict(list)
            for turn_transition, changes in judge_changes.items():
                filtered_judge_changes[turn_transition] = [c for c in changes if c != 0]
            plot_data.append((label, filtered_judge_changes, color))
        else:
            plot_data.append((label, judge_changes, color))

    # Plot each column (judge)
    for col, (label, changes_by_turn, base_color) in enumerate(plot_data):
        # Create custom colormap from white to base color
        cmap = mcolors.LinearSegmentedColormap.from_list(
            f'white_to_{label}', ['white', base_color])

        # Top row: raw differences (-10 to +10)
        ax_diff = axes[0, col]

        # Build heatmap matrix: rows are change values, columns are turn transitions
        change_values_raw = list(range(-10, 11))  # -10 to 10
        heatmap_raw = np.zeros((len(change_values_raw), len(turn_transitions)))

        for i, turn_transition in enumerate(turn_transitions):
            changes = changes_by_turn[turn_transition]
            if changes:
                # Count occurrences of each change value
                for change in changes:
                    change_idx = change + 10  # Map -10→0, ..., 0→10, ..., 10→20
                    if 0 <= change_idx < len(change_values_raw):
                        heatmap_raw[change_idx, i] += 1

                # Normalize per column (turn) to get proportions
                column_sum = heatmap_raw[:, i].sum()
                if column_sum > 0:
                    heatmap_raw[:, i] /= column_sum

        # Plot heatmap (flip vertically so -10 is at bottom, +10 at top)
        im_diff = ax_diff.imshow(np.flipud(heatmap_raw), cmap=cmap, aspect='auto',
                                interpolation='nearest', vmin=0, vmax=1)
        ax_diff.set_title(f'{label}', fontsize=11, fontweight='bold')
        ax_diff.set_xticks(range(len(turn_transitions)))
        ax_diff.set_xticklabels(turn_labels, fontsize=9)
        ax_diff.set_yticks(range(0, 21, 5))
        ax_diff.set_yticklabels([10, 5, 0, -5, -10], fontsize=9)
        if col == 0:
            ax_diff.set_ylabel('Score Change', fontsize=10)

        # Bottom row: absolute values (0 to 10)
        ax_abs = axes[1, col]

        change_values_abs = list(range(0, 11))  # 0 to 10
        heatmap_abs = np.zeros((len(change_values_abs), len(turn_transitions)))

        for i, turn_transition in enumerate(turn_transitions):
            changes = changes_by_turn[turn_transition]
            if changes:
                # Count occurrences of each absolute change value
                for change in changes:
                    abs_change = abs(change)
                    if 0 <= abs_change < len(change_values_abs):
                        heatmap_abs[abs_change, i] += 1

                # Normalize per column (turn) to get proportions
                column_sum = heatmap_abs[:, i].sum()
                if column_sum > 0:
                    heatmap_abs[:, i] /= column_sum

        # Plot heatmap (flip vertically so 0 is at bottom, 10 at top)
        im_abs = ax_abs.imshow(np.flipud(heatmap_abs), cmap=cmap, aspect='auto',
                              interpolation='nearest', vmin=0, vmax=1)
        ax_abs.set_xticks(range(len(turn_transitions)))
        ax_abs.set_xticklabels(turn_labels, fontsize=9)
        ax_abs.set_yticks(range(0, 11, 2))
        ax_abs.set_yticklabels([10, 8, 6, 4, 2, 0], fontsize=9)
        if col == 0:
            ax_abs.set_ylabel('Absolute Value of Score Change', fontsize=10)
        ax_abs.set_xlabel('Turn Transition', fontsize=10)

    # Overall title
    fig.suptitle('Judge Score Changes Between Consecutive Turns (Normalized Per Turn)',
                fontsize=14, fontweight='bold', y=0.995)

    plt.tight_layout()
    plt.savefig(output_filename, dpi=150, bbox_inches='tight')
    print(f'Saved to {output_filename}')
    plt.close()

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Create judge score change heatmaps')
    parser.add_argument('--exclude-zeros', action='store_true',
                       help='Exclude zero changes from the visualization')
    args = parser.parse_args()

    # Create output directory
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                              'plotting', 'plots', 'judge-score-change-histogram')
    os.makedirs(output_dir, exist_ok=True)

    if args.exclude_zeros:
        output_path = os.path.join(output_dir, 'judge-score-changes_no_zeros.png')
    else:
        output_path = os.path.join(output_dir, 'judge-score-changes.png')

    create_score_change_heatmap(output_path, exclude_zeros=args.exclude_zeros)
