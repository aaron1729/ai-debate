import sqlite3
import os
from claim_shortnames import CLAIM_SHORTNAMES

def cleanup_and_rename_misc_debates():
    """
    1. Delete individual plots from score-by-turn/ that have been paired
    2. Rename remaining single plots with shortnames
    """
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'experiments.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all experiment 4-tuples
    cursor.execute('''
        SELECT claim, pro_model, con_model, judge_model, COUNT(*) as num_turns, GROUP_CONCAT(turns) as turn_list
        FROM experiments
        WHERE judge_score IS NOT NULL
        GROUP BY claim, pro_model, con_model, judge_model
        HAVING COUNT(*) = 4 AND turn_list = '1,2,4,6'
    ''')

    all_experiments = cursor.fetchall()

    # Identify which are paired
    # Group by claim and sorted debater pair
    pairs_dict = {}
    for claim, pro_model, con_model, judge_model, _, _ in all_experiments:
        debater1 = min(pro_model, con_model)
        debater2 = max(pro_model, con_model)
        key = (claim, debater1, debater2, judge_model)

        if key not in pairs_dict:
            pairs_dict[key] = []
        pairs_dict[key].append((pro_model, con_model))

    # Identify paired vs single experiments
    paired_experiments = set()
    single_experiments = []

    for key, orientations in pairs_dict.items():
        claim, debater1, debater2, judge_model = key
        if len(orientations) == 2:
            # This is a paired experiment
            paired_experiments.add((claim, debater1, debater2, judge_model))
            paired_experiments.add((claim, debater2, debater1, judge_model))
        else:
            # Single experiment
            for pro_model, con_model in orientations:
                single_experiments.append((claim, pro_model, con_model, judge_model))

    conn.close()

    model_map = {
        'claude-sonnet-4-5-20250929': 'claude',
        'gemini-2.5-flash': 'gemini',
        'gpt-4-turbo-preview': 'gpt4',
        'grok-3': 'grok'
    }

    misc_debates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                    'plotting', 'plots', 'score-by-turn')

    # Step 1: Delete paired plots from score-by-turn/
    print("Deleting paired plots from score-by-turn/...")
    deleted_count = 0

    for claim, pro_model, con_model, judge_model, _, _ in all_experiments:
        if (claim, pro_model, con_model, judge_model) in paired_experiments:
            # This was part of a pair, delete it
            pro_short = model_map.get(pro_model, pro_model)
            con_short = model_map.get(con_model, con_model)
            judge_short = model_map.get(judge_model, judge_model)

            # Find matching file (starts with claim shortname pattern)
            for filename in os.listdir(misc_debates_dir):
                if (f'__pro_{pro_short}__con_{con_short}__judge_{judge_short}.png' in filename):
                    filepath = os.path.join(misc_debates_dir, filename)
                    print(f'  Deleting: {filename}')
                    os.remove(filepath)
                    deleted_count += 1
                    break

    print(f"Deleted {deleted_count} paired plots")

    # Step 2: Rename remaining single plots
    print("\nRenaming single plots with shortnames...")
    renamed_count = 0

    for claim, pro_model, con_model, judge_model in single_experiments:
        shortname = CLAIM_SHORTNAMES.get(claim, 'unknown')
        pro_short = model_map.get(pro_model, pro_model)
        con_short = model_map.get(con_model, con_model)
        judge_short = model_map.get(judge_model, judge_model)

        # Find old filename
        old_pattern = f'__pro_{pro_short}__con_{con_short}__judge_{judge_short}.png'
        old_filename = None
        for filename in os.listdir(misc_debates_dir):
            if old_pattern in filename:
                old_filename = filename
                break

        if old_filename:
            new_filename = f'{shortname}_pro-{pro_short}_con-{con_short}_judge-{judge_short}.png'
            old_path = os.path.join(misc_debates_dir, old_filename)
            new_path = os.path.join(misc_debates_dir, new_filename)

            print(f'  Renaming: {old_filename} -> {new_filename}')
            os.rename(old_path, new_path)
            renamed_count += 1

    print(f"\nRenamed {renamed_count} single plots")
    print(f"Total files remaining in score-by-turn/: {len(os.listdir(misc_debates_dir))}")

if __name__ == '__main__':
    cleanup_and_rename_misc_debates()
