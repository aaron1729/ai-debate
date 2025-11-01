import sqlite3
import matplotlib.pyplot as plt
import numpy as np

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

# Fixed ordering for models (used to determine offsets when scores collide)
# Higher in hierarchy = higher on plot when colliding
MODEL_ORDER = {
    'claude-sonnet-4-5-20250929': 0,  # highest priority
    'gemini-2.5-flash': 1,
    'gpt-4-turbo-preview': 2,
    'grok-3': 3  # lowest priority
}

PRO_COLOR = '#007000'  # green
CON_COLOR = '#D22222'  # red

def calculate_offsets(judge_data):
    """
    Calculate offsets for each model based on score collisions.
    Returns a dict mapping (judge_model, turn) -> offset
    """
    offsets = {}

    # Get all turns
    all_turns = set()
    for data in judge_data.values():
        all_turns.update(data['turns'])

    # For each turn, check which models have colliding scores
    for turn in all_turns:
        scores_at_turn = []
        for judge_model, data in judge_data.items():
            if turn in data['turns']:
                idx = data['turns'].index(turn)
                score = data['scores'][idx]
                # Treat None as 5 for collision detection
                actual_score = 5 if score is None else score
                scores_at_turn.append((judge_model, actual_score))

        # Group by score to find collisions
        score_groups = {}
        for judge_model, score in scores_at_turn:
            # Round to 1 decimal to detect collisions
            rounded = round(score, 1)
            if rounded not in score_groups:
                score_groups[rounded] = []
            score_groups[rounded].append(judge_model)

        # Assign offsets for colliding models
        for score, models in score_groups.items():
            if len(models) > 1:
                # Sort by model order (lower order = higher on plot)
                models.sort(key=lambda m: MODEL_ORDER.get(m, 999))
                # Calculate offsets based on count (higher order = higher offset = higher on plot)
                if len(models) == 2:
                    offset_values = [0.1, -0.1]  # first model (lower order) gets positive offset
                elif len(models) == 3:
                    offset_values = [0.15, 0, -0.15]
                else:  # 4 or more
                    offset_values = [0.15, 0.05, -0.05, -0.15]

                for i, model in enumerate(models):
                    offsets[(model, turn)] = offset_values[i]
            else:
                # No collision, no offset
                offsets[(models[0], turn)] = 0

    return offsets

def create_debate_plot(motion_pattern, output_filename):
    conn = sqlite3.connect('experiments.db')
    cursor = conn.cursor()

    cursor.execute(f'''
        SELECT id, claim, pro_model, con_model, pro_went_first
        FROM experiments
        WHERE claim LIKE ?
        ORDER BY id
    ''', (motion_pattern,))

    experiments = cursor.fetchall()
    if not experiments:
        print(f'No experiments found for pattern: {motion_pattern}')
        return

    motion_text = experiments[0][1]

    fig, axes = plt.subplots(2, 2, figsize=(18, 11))
    # Adjust spacing to make room for outer labels
    # Push plots down even more to give plenty of room for column labels
    fig.subplots_adjust(hspace=0.40, wspace=0.35, top=0.76, bottom=0.10, left=0.14, right=0.97)
    # Add more space around main title (both above and below)
    fig.suptitle(f'Debate Motion: {motion_text}', fontsize=13, fontweight='bold', y=0.93)

    axes = axes.flatten()

    # Add outer labels with much more spacing
    # Top labels (order: Pro, then Con; Con, then Pro) - positioned well above the subplots with plenty of padding below
    fig.text(0.37, 0.82, 'Pro, then Con', fontsize=11, ha='center', fontweight='bold', color='#555555')
    fig.text(0.76, 0.82, 'Con, then Pro', fontsize=11, ha='center', fontweight='bold', color='#555555')

    # Left labels (debater assignments) - more padding from edge, adjusted for new vertical spacing
    fig.text(0.04, 0.57, 'Pro = Claude, Con = Grok', fontsize=11, ha='left', va='center',
             rotation=90, fontweight='bold', color='#555555')
    fig.text(0.04, 0.27, 'Pro = Grok, Con = Claude', fontsize=11, ha='left', va='center',
             rotation=90, fontweight='bold', color='#555555')

    for idx, (exp_id, claim, pro_model, con_model, pro_went_first) in enumerate(experiments):
        ax = axes[idx]

        cursor.execute('''
            SELECT judge_model, turns_considered, score
            FROM judgments
            WHERE experiment_id = ?
            ORDER BY judge_model, turns_considered
        ''', (exp_id,))

        judgments = cursor.fetchall()

        judge_data = {}
        for judge_model, turns, score in judgments:
            if judge_model not in judge_data:
                judge_data[judge_model] = {'turns': [], 'scores': []}
            judge_data[judge_model]['turns'].append(turns)
            judge_data[judge_model]['scores'].append(score)

        # Calculate offsets based on collisions
        offsets = calculate_offsets(judge_data)

        for judge_model in sorted(judge_data.keys()):
            data = judge_data[judge_model]
            turns = data['turns']
            scores = data['scores']

            color = MODEL_COLORS.get(judge_model, '#666666')
            label = MODEL_LABELS.get(judge_model, judge_model)

            # Build arrays for plotting with dynamic offsets
            all_turns = turns
            all_scores_with_offset = []
            for i, (t, s) in enumerate(zip(turns, scores)):
                offset = offsets.get((judge_model, t), 0)
                actual_score = 5 if s is None else s
                all_scores_with_offset.append(actual_score + offset)

            # Plot line segments
            for i in range(len(all_turns) - 1):
                has_none = (scores[i] is None or scores[i+1] is None)
                linestyle = '--' if has_none else '-'
                ax.plot([all_turns[i], all_turns[i+1]],
                       [all_scores_with_offset[i], all_scores_with_offset[i+1]],
                       linestyle, color=color, linewidth=2, alpha=0.8)

            # Plot markers with smaller open circles
            for t, s in zip(turns, scores):
                offset = offsets.get((judge_model, t), 0)
                if s is not None:
                    ax.plot(t, s + offset, 'o', color=color, markersize=6, alpha=0.8)
                else:
                    # Smaller open circle - markersize 6 instead of default
                    ax.plot(t, 5 + offset, 'o', color=color, markersize=6,
                           fillstyle='none', markeredgewidth=1.5, alpha=0.8)

            # Legend (only first subplot)
            if idx == 0:
                ax.plot([], [], 'o-', color=color, label=label, linewidth=2, markersize=6)

        # Build title
        pro_short = MODEL_LABELS.get(pro_model, 'Unknown')
        con_short = MODEL_LABELS.get(con_model, 'Unknown')
        pro_color = MODEL_COLORS.get(pro_model, '#666666')
        con_color = MODEL_COLORS.get(con_model, '#666666')

        ax.set_title('')

        # Build title text with color codes
        from matplotlib import patheffects

        # Just build the title text, we'll create it piece by piece below
        if pro_went_first:
            title_text = f'{pro_short} arguing Pro, then {con_short} arguing Con'
        else:
            title_text = f'{con_short} arguing Con, then {pro_short} arguing Pro'

        # Split and color manually
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

        # Calculate positions manually with better precision
        full_str = ''.join([w[0] for w in words])

        # Use figure coordinates for better control
        # Create a temporary text to measure
        temp_t = ax.text(0, 0, full_str, fontsize=11, fontweight='bold', alpha=0)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        bbox_full = temp_t.get_window_extent(renderer=renderer)
        temp_t.remove()

        # Now place each word
        current_pos = 0
        for word, color in words:
            # Create temp text to measure this word
            temp_w = ax.text(0, 0, word, fontsize=11, fontweight='bold', alpha=0)
            fig.canvas.draw()
            bbox_word = temp_w.get_window_extent(renderer=renderer)
            word_width = bbox_word.width
            temp_w.remove()

            # Position in axes coordinates
            # Start from left edge of full text and offset by current_pos
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

    # Add note at the bottom
    note_text = ('An open circle denotes a "needs more evidence" ruling (not actually scored, but plotted here as 5).\n'
                 'Dashed lines are used to connect these rulings to others.')
    fig.text(0.5, 0.02, note_text, fontsize=8, ha='center', va='bottom', style='italic', color='#666666')

    plt.savefig(output_filename, dpi=150, bbox_inches='tight')
    print(f'Saved to {output_filename}')
    conn.close()

def create_debate_plot_from_ids(experiment_ids, output_filename):
    """Create a debate plot from a list of experiment IDs."""
    conn = sqlite3.connect('experiments.db')
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
    fig.suptitle(f'Debate Motion: {motion_text}', fontsize=13, fontweight='bold', y=0.93)

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
        model1, model2 = sorted(all_models)  # Alphabetically sorted
        label1 = f'{MODEL_LABELS.get(model1, "Model1")} vs {MODEL_LABELS.get(model2, "Model2")}'
        label2 = label1  # Same label for both rows since they're swapped

        fig.text(0.04, 0.57, f'Pro = {MODEL_LABELS.get(experiments[0][2])}, Con = {MODEL_LABELS.get(experiments[0][3])}',
                 fontsize=11, ha='left', va='center', rotation=90, fontweight='bold', color='#555555')
        fig.text(0.04, 0.27, f'Pro = {MODEL_LABELS.get(experiments[2][2])}, Con = {MODEL_LABELS.get(experiments[2][3])}',
                 fontsize=11, ha='left', va='center', rotation=90, fontweight='bold', color='#555555')

    for idx, (exp_id, claim, pro_model, con_model, pro_went_first) in enumerate(experiments):
        ax = axes[idx]

        cursor.execute('''
            SELECT judge_model, turns_considered, score
            FROM judgments
            WHERE experiment_id = ?
            ORDER BY judge_model, turns_considered
        ''', (exp_id,))

        judgments = cursor.fetchall()

        judge_data = {}
        for judge_model, turns, score in judgments:
            if judge_model not in judge_data:
                judge_data[judge_model] = {'turns': [], 'scores': []}
            judge_data[judge_model]['turns'].append(turns)
            judge_data[judge_model]['scores'].append(score)

        offsets = calculate_offsets(judge_data)

        for judge_model in sorted(judge_data.keys()):
            data = judge_data[judge_model]
            turns = data['turns']
            scores = data['scores']

            color = MODEL_COLORS.get(judge_model, '#666666')
            label = MODEL_LABELS.get(judge_model, judge_model)

            all_turns = turns
            all_scores_with_offset = []
            for i, (t, s) in enumerate(zip(turns, scores)):
                offset = offsets.get((judge_model, t), 0)
                actual_score = 5 if s is None else s
                all_scores_with_offset.append(actual_score + offset)

            for i in range(len(all_turns) - 1):
                has_none = (scores[i] is None or scores[i+1] is None)
                linestyle = '--' if has_none else '-'
                ax.plot([all_turns[i], all_turns[i+1]],
                       [all_scores_with_offset[i], all_scores_with_offset[i+1]],
                       linestyle, color=color, linewidth=2, alpha=0.8)

            for t, s in zip(turns, scores):
                offset = offsets.get((judge_model, t), 0)
                if s is not None:
                    ax.plot(t, s + offset, 'o', color=color, markersize=6, alpha=0.8)
                else:
                    ax.plot(t, 5 + offset, 'o', color=color, markersize=6,
                           fillstyle='none', markeredgewidth=1.5, alpha=0.8)

            if idx == 0:
                ax.plot([], [], 'o-', color=color, label=label, linewidth=2, markersize=6)

        pro_short = MODEL_LABELS.get(pro_model, 'Unknown')
        con_short = MODEL_LABELS.get(con_model, 'Unknown')
        pro_color = MODEL_COLORS.get(pro_model, '#666666')
        con_color = MODEL_COLORS.get(con_model, '#666666')

        ax.set_title('')

        from matplotlib import patheffects

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
                 'Dashed lines are used to connect these rulings to others.')
    fig.text(0.5, 0.02, note_text, fontsize=8, ha='center', va='bottom', style='italic', color='#666666')

    plt.savefig(output_filename, dpi=150, bbox_inches='tight')
    print(f'Saved to {output_filename}')
    conn.close()

if __name__ == '__main__':
    create_debate_plot('%political correctness%', 'political_correctness_debates.png')
