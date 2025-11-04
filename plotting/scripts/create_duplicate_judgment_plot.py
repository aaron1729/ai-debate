#!/usr/bin/env python3
"""Create plots showing duplicate judgments for judge consistency analysis."""

import sqlite3
import matplotlib.pyplot as plt
from create_debate_plot import MODEL_COLORS, MODEL_LABELS, MODEL_ORDER, PRO_COLOR, CON_COLOR, calculate_offsets

def create_duplicate_judgment_plot(experiment_ids, output_filename):
    """
    Create a debate plot showing ALL judgments (including duplicates) for experiments.
    This allows visualizing judge consistency by showing multiple curves for the same judge.
    """
    import os
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'experiments.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Fetch experiments by IDs
    placeholders = ','.join('?' * len(experiment_ids))
    cursor.execute(f'''
        SELECT id, claim, pro_model, con_model, pro_went_first
        FROM experiments
        WHERE id IN ({placeholders})
        ORDER BY id
    ''', experiment_ids)

    experiments = cursor.fetchall()
    if not experiments:
        print(f'No experiments found for IDs: {experiment_ids}')
        return

    if len(experiments) != 4:
        print(f'Warning: Expected 4 experiments, found {len(experiments)}')

    motion_text = experiments[0][1]

    fig, axes = plt.subplots(2, 2, figsize=(18, 11))
    fig.subplots_adjust(hspace=0.40, wspace=0.35, top=0.76, bottom=0.10, left=0.14, right=0.97)
    fig.suptitle(f'Debate Motion (Duplicate Judgments for Consistency): {motion_text}', fontsize=13, fontweight='bold', y=0.93)

    axes = axes.flatten()

    fig.text(0.37, 0.82, 'Pro, then Con', fontsize=11, ha='center', fontweight='bold', color='#555555')
    fig.text(0.76, 0.82, 'Con, then Pro', fontsize=11, ha='center', fontweight='bold', color='#555555')

    # Determine debaters from experiments
    pro_models = set()
    con_models = set()
    for exp in experiments:
        pro_models.add(exp[2])
        con_models.add(exp[3])

    # Get the two unique models (assuming only 2 models debated)
    all_models = list(pro_models | con_models)
    if len(all_models) == 2:
        fig.text(0.04, 0.57, f'Pro = {MODEL_LABELS.get(experiments[0][2])}, Con = {MODEL_LABELS.get(experiments[0][3])}',
                 fontsize=11, ha='left', va='center', rotation=90, fontweight='bold', color='#555555')
        fig.text(0.04, 0.27, f'Pro = {MODEL_LABELS.get(experiments[2][2])}, Con = {MODEL_LABELS.get(experiments[2][3])}',
                 fontsize=11, ha='left', va='center', rotation=90, fontweight='bold', color='#555555')

    for idx, (exp_id, claim, pro_model, con_model, pro_went_first) in enumerate(experiments):
        ax = axes[idx]

        # Query ALL judgments WITHOUT deduplication
        cursor.execute('''
            SELECT id, judge_model, turns_considered, score
            FROM judgments
            WHERE experiment_id = ?
            ORDER BY judge_model, turns_considered, id
        ''', (exp_id,))

        judgments = cursor.fetchall()

        # Group by (judge_model, id_batch) to separate the two runs
        # We'll identify batches by looking at gaps in IDs
        judge_batches = {}
        for judgment_id, judge_model, turns, score in judgments:
            if judge_model not in judge_batches:
                judge_batches[judge_model] = []
            judge_batches[judge_model].append((judgment_id, turns, score))

        # For each judge, split into batches based on ID gaps
        judge_curves = {}
        for judge_model, data_points in judge_batches.items():
            # Sort by ID
            data_points.sort(key=lambda x: x[0])

            # Split into batches based on large ID gaps (>100 suggests different runs)
            batches = []
            current_batch = [data_points[0]]

            for i in range(1, len(data_points)):
                prev_id = data_points[i-1][0]
                curr_id = data_points[i][0]

                if curr_id - prev_id > 100:  # Large gap = new batch
                    batches.append(current_batch)
                    current_batch = [data_points[i]]
                else:
                    current_batch.append(data_points[i])

            batches.append(current_batch)
            judge_curves[judge_model] = batches

        # Now plot each batch as a separate curve
        for judge_model in sorted(judge_curves.keys()):
            batches = judge_curves[judge_model]
            color = MODEL_COLORS.get(judge_model, '#666666')
            label = MODEL_LABELS.get(judge_model, judge_model)

            for batch_idx, batch in enumerate(batches):
                # Extract turns and scores from batch
                turns = [point[1] for point in batch]
                scores = [point[2] for point in batch]

                # Calculate alpha and linestyle for multiple batches
                alpha = 0.8 if batch_idx == 0 else 0.4
                linewidth = 2 if batch_idx == 0 else 1.5

                # Plot line segments
                for i in range(len(turns) - 1):
                    has_none = (scores[i] is None or scores[i+1] is None)
                    linestyle = '--' if has_none else '-'
                    actual_scores = [5 if s is None else s for s in [scores[i], scores[i+1]]]
                    ax.plot([turns[i], turns[i+1]],
                           actual_scores,
                           linestyle, color=color, linewidth=linewidth, alpha=alpha)

                # Plot markers
                for t, s in zip(turns, scores):
                    if s is not None:
                        ax.plot(t, s, 'o', color=color, markersize=6, alpha=alpha)
                    else:
                        ax.plot(t, 5, 'o', color=color, markersize=6,
                               fillstyle='none', markeredgewidth=1.5, alpha=alpha)

            # Legend (only first subplot, only first batch)
            if idx == 0:
                ax.plot([], [], 'o-', color=color, label=label, linewidth=2, markersize=6)

        pro_short = MODEL_LABELS.get(pro_model, 'Unknown')
        con_short = MODEL_LABELS.get(con_model, 'Unknown')
        pro_color = MODEL_COLORS.get(pro_model, '#666666')
        con_color = MODEL_COLORS.get(con_model, '#666666')

        ax.set_title('')

        # Build title with colored text
        if pro_went_first:
            words = [
                (pro_short, pro_color),
                (' arguing ', 'black'),
                ('Pro', PRO_COLOR),
                (', then ', 'black'),
                (con_short, con_color),
                (' arguing ', 'black'),
                ('Con', CON_COLOR)
            ]
        else:
            words = [
                (con_short, con_color),
                (' arguing ', 'black'),
                ('Con', CON_COLOR),
                (', then ', 'black'),
                (pro_short, pro_color),
                (' arguing ', 'black'),
                ('Pro', PRO_COLOR)
            ]

        full_str = ''.join([w[0] for w in words])

        temp_t = ax.text(0, 0, full_str, fontsize=11, fontweight='bold', alpha=0)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        bbox_full = temp_t.get_window_extent(renderer=renderer)
        temp_t.remove()

        current_pos = 0
        for word, color in words:
            temp_w = ax.text(0, 0, word, fontsize=11, fontweight='bold', alpha=0)
            fig.canvas.draw()
            bbox_word = temp_w.get_window_extent(renderer=renderer)
            word_width = bbox_word.width
            temp_w.remove()

            start_axes = 0.5 - (bbox_full.width / 2) / (ax.bbox.width)
            word_axes_pos = start_axes + current_pos / ax.bbox.width

            ax.text(word_axes_pos, 1.06, word, color=color, fontsize=11,
                   fontweight='bold', transform=ax.transAxes, va='bottom', ha='left')

            current_pos += word_width

        ax.set_xlabel('Debate Turn', fontsize=10)
        ax.set_ylabel('Score', fontsize=10)
        ax.set_xticks(range(1, 7))
        ax.set_ylim(0, 10)
        ax.grid(True, alpha=0.3)

        ax.text(0.5, 1, 'Contradicted', fontsize=9, alpha=0.7, style='italic',
                color=CON_COLOR, fontweight='bold')
        ax.text(0.5, 9, 'Supported', fontsize=9, alpha=0.7, style='italic',
                color=PRO_COLOR, fontweight='bold')

        if idx == 0:
            ax.legend(loc='best', fontsize=9)

    note_text = ('An open circle denotes a "needs more evidence" ruling (not actually scored, but plotted here as 5).\n'
                 'Dashed lines are used to connect these rulings to others. Faded curves show duplicate judgments.')
    fig.text(0.5, 0.02, note_text, fontsize=8, ha='center', va='bottom', style='italic', color='#666666')

    plt.savefig(output_filename, dpi=150, bbox_inches='tight')
    print(f'Saved to {output_filename}')
    conn.close()

if __name__ == '__main__':
    # Plot the 4 experiments that have duplicate judgments (223, 255, 256, 257)
    create_duplicate_judgment_plot(
        [223, 255, 256, 257],
        'plotting/plots/debate-motions-with-duplicate-judging/debate_consistency_test.png'
    )
