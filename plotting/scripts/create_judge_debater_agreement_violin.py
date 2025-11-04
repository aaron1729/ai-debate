#!/usr/bin/env python3
"""Create judge-debater agreement violin plot grid (4x5)."""

import sqlite3
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
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

# Pro/Con colors from debate plots
PRO_COLOR = '#007000'  # green
CON_COLOR = '#D22222'  # red

def create_judge_debater_agreement_violin(output_filename):
    """Create a 4x5 grid of violin plots showing score distributions.

    Rows: Judges (Claude, Gemini, GPT-4, Grok)
    Column 1: Overall score distribution for that judge
    Columns 2-5: Split violins for each debater (Con=red left, Pro=green right)

    Args:
        output_filename: Path to save the plot
    """

    # Connect to database
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'experiments.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # All models in order
    models = [
        'claude-sonnet-4-5-20250929',
        'gemini-2.5-flash',
        'gpt-4-turbo-preview',
        'grok-3'
    ]

    # Create figure with 4x5 subplots - add more top space
    fig, axes = plt.subplots(4, 5, figsize=(24, 16))

    # Adjust layout first to get accurate subplot positions
    plt.tight_layout(rect=[0, 0.02, 1, 0.93])

    fig.suptitle('Judge-Debater Agreement', fontsize=18, fontweight='bold', y=0.985)

    # Add column headers - align properly with columns using actual positions
    # Calculate positions after tight_layout
    header_y = 0.945  # Position below title, above plots

    # First column header
    ax0_bbox = axes[0, 0].get_position()
    col0_center_x = ax0_bbox.x0 + (ax0_bbox.x1 - ax0_bbox.x0) / 2
    fig.text(col0_center_x, header_y,
             'Overall Score\nDistribution', fontsize=12, ha='center', fontweight='bold')

    # Debater column headers - calculate center of each column
    for col_idx, debater_id in enumerate(models):
        debater_label = MODEL_LABELS.get(debater_id, debater_id)
        ax_bbox = axes[0, col_idx + 1].get_position()
        col_center_x = ax_bbox.x0 + (ax_bbox.x1 - ax_bbox.x0) / 2
        fig.text(col_center_x, header_y,
                f'Debater:\n{debater_label}',
                fontsize=12, ha='center', fontweight='bold')

    # Process each judge (row)
    for row_idx, judge_id in enumerate(models):
        judge_label = MODEL_LABELS.get(judge_id, judge_id)
        judge_color = MODEL_COLORS.get(judge_id, '#666666')

        # Column 0: Overall distribution
        ax = axes[row_idx, 0]

        # Query all scores for this judge
        cursor.execute('''
            SELECT score
            FROM judgments
            WHERE judge_model = ? AND score IS NOT NULL
        ''', (judge_id,))
        all_scores = [row[0] for row in cursor.fetchall()]

        if all_scores:
            # Calculate KDE for normalized violin
            kde = stats.gaussian_kde(all_scores)
            y_range = np.linspace(0, 10, 200)
            density = kde(y_range)
            # Normalize density to have consistent visual area
            density = density / np.max(density) * 0.35  # Scale to violin width

            # Plot violin
            ax.fill_betweenx(y_range, -density, density, facecolor=judge_color,
                           alpha=0.7, edgecolor='black', linewidth=1.5)

            # Add mean and median markers
            mean_val = np.mean(all_scores)
            median_val = np.median(all_scores)

            # Offset horizontally if mean and median are too close
            if abs(mean_val - median_val) < 0.3:
                # Offset mean to left, median to right
                ax.plot([-0.05], [mean_val], 'D', color='white', markersize=8,
                       markeredgecolor='black', markeredgewidth=1.5, zorder=10)
                ax.plot([0.05], [median_val], 'o', color='black', markersize=8,
                       markeredgecolor='black', markeredgewidth=1.5, zorder=10)
            else:
                # Plot at center
                ax.plot([0], [mean_val], 'D', color='white', markersize=8,
                       markeredgecolor='black', markeredgewidth=1.5, zorder=10)
                ax.plot([0], [median_val], 'o', color='black', markersize=8,
                       markeredgecolor='black', markeredgewidth=1.5, zorder=10)

        ax.set_ylim(-0.5, 10.5)
        ax.set_yticks(range(0, 11))
        ax.set_xlim(-0.5, 0.5)
        ax.set_xticks([])
        ax.grid(True, alpha=0.3, axis='y')

        # Add judge label on left
        if row_idx == 0:
            ax.set_ylabel(f'Judge: {judge_label}\n\nScore', fontsize=11, fontweight='bold')
        else:
            ax.set_ylabel(f'Judge: {judge_label}\n\nScore', fontsize=11, fontweight='bold')

        # Columns 1-4: Split violins for each debater
        for col_idx, debater_id in enumerate(models):
            ax = axes[row_idx, col_idx + 1]

            # Query scores when debater is Pro
            cursor.execute('''
                SELECT j.score
                FROM judgments j
                JOIN experiments e ON j.experiment_id = e.id
                WHERE j.judge_model = ?
                AND e.pro_model = ?
                AND j.score IS NOT NULL
            ''', (judge_id, debater_id))
            pro_scores = [row[0] for row in cursor.fetchall()]

            # Query scores when debater is Con
            cursor.execute('''
                SELECT j.score
                FROM judgments j
                JOIN experiments e ON j.experiment_id = e.id
                WHERE j.judge_model = ?
                AND e.con_model = ?
                AND j.score IS NOT NULL
            ''', (judge_id, debater_id))
            con_scores = [row[0] for row in cursor.fetchall()]

            # Create split violin plot with shared centerline
            y_range = np.linspace(0, 10, 200)

            # Con scores (left side, red)
            if con_scores:
                kde_con = stats.gaussian_kde(con_scores)
                density_con = kde_con(y_range)
                # Normalize density to have consistent visual area
                density_con = density_con / np.max(density_con) * 0.35

                # Plot left half only (negative x)
                ax.fill_betweenx(y_range, 0, -density_con, facecolor=CON_COLOR,
                               alpha=0.7, edgecolor='black', linewidth=1.5)

                # Add mean and median markers for Con
                mean_con = np.mean(con_scores)
                median_con = np.median(con_scores)

                # Interpolate density at mean/median positions
                mean_density = np.interp(mean_con, y_range, density_con)
                median_density = np.interp(median_con, y_range, density_con)

                # Offset horizontally if mean and median are too close
                if abs(mean_con - median_con) < 0.3:
                    # Offset: mean closer to center, median further out
                    ax.plot([-mean_density/3], [mean_con], 'D', color='white', markersize=6,
                           markeredgecolor='black', markeredgewidth=1.5, zorder=10)
                    ax.plot([-mean_density*0.7], [median_con], 'o', color='black', markersize=6,
                           markeredgecolor='black', markeredgewidth=1.5, zorder=10)
                else:
                    ax.plot([-mean_density/2], [mean_con], 'D', color='white', markersize=6,
                           markeredgecolor='black', markeredgewidth=1.5, zorder=10)
                    ax.plot([-median_density/2], [median_con], 'o', color='black', markersize=6,
                           markeredgecolor='black', markeredgewidth=1.5, zorder=10)

            # Pro scores (right side, green)
            if pro_scores:
                kde_pro = stats.gaussian_kde(pro_scores)
                density_pro = kde_pro(y_range)
                # Normalize density to have consistent visual area
                density_pro = density_pro / np.max(density_pro) * 0.35

                # Plot right half only (positive x)
                ax.fill_betweenx(y_range, 0, density_pro, facecolor=PRO_COLOR,
                               alpha=0.7, edgecolor='black', linewidth=1.5)

                # Add mean and median markers for Pro
                mean_pro = np.mean(pro_scores)
                median_pro = np.median(pro_scores)

                # Interpolate density at mean/median positions
                mean_density = np.interp(mean_pro, y_range, density_pro)
                median_density = np.interp(median_pro, y_range, density_pro)

                # Offset horizontally if mean and median are too close
                if abs(mean_pro - median_pro) < 0.3:
                    # Offset: mean closer to center, median further out
                    ax.plot([mean_density/3], [mean_pro], 'D', color='white', markersize=6,
                           markeredgecolor='black', markeredgewidth=1.5, zorder=10)
                    ax.plot([mean_density*0.7], [median_pro], 'o', color='black', markersize=6,
                           markeredgecolor='black', markeredgewidth=1.5, zorder=10)
                else:
                    ax.plot([mean_density/2], [mean_pro], 'D', color='white', markersize=6,
                           markeredgecolor='black', markeredgewidth=1.5, zorder=10)
                    ax.plot([median_density/2], [median_pro], 'o', color='black', markersize=6,
                           markeredgecolor='black', markeredgewidth=1.5, zorder=10)

            ax.set_ylim(-0.5, 10.5)
            ax.set_yticks(range(0, 11))
            if col_idx == 0:
                ax.set_yticklabels([])  # Hide y-tick labels for columns 2-5
            else:
                ax.set_yticklabels([])
            ax.set_xlim(-0.5, 0.5)
            ax.set_xticks([])
            ax.grid(True, alpha=0.3, axis='y')

    conn.close()

    # Add legend
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    legend_elements = [
        Patch(facecolor=CON_COLOR, edgecolor='black', alpha=0.7, label='Arguing Con (lower scores)'),
        Patch(facecolor=PRO_COLOR, edgecolor='black', alpha=0.7, label='Arguing Pro (higher scores)'),
        Line2D([0], [0], marker='D', color='w', markerfacecolor='white',
               markeredgecolor='black', markeredgewidth=1.5, markersize=8,
               linestyle='None', label='Mean'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='black',
               markeredgecolor='black', markeredgewidth=1.5, markersize=8,
               linestyle='None', label='Median')
    ]
    fig.legend(handles=legend_elements, loc='lower center', ncol=4, fontsize=11,
              bbox_to_anchor=(0.5, -0.01), frameon=True)

    plt.savefig(output_filename, dpi=150, bbox_inches='tight')
    print(f'Saved to {output_filename}')
    plt.close()

if __name__ == '__main__':
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                              'plotting', 'plots', 'judge-debater-agreement-violin')
    os.makedirs(output_dir, exist_ok=True)

    create_judge_debater_agreement_violin(
        os.path.join(output_dir, 'judge_debater_agreement_violin_grid.png')
    )
