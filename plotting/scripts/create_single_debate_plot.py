#!/usr/bin/env python3
"""
Generate a judge-score plot for a single debate experiment.

This mirrors the styling of the per-condition plots produced by create_debate_plot.py
but focuses on one experiment (one debate configuration).
"""

import argparse
import sqlite3
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt

from create_debate_plot import (
    MODEL_COLORS,
    MODEL_LABELS,
    PRO_COLOR,
    CON_COLOR,
    calculate_offsets,
)


def fetch_experiment(cursor: sqlite3.Cursor, experiment_id: int) -> Tuple[str, str, str, bool]:
    cursor.execute(
        """
        SELECT claim, pro_model, con_model, pro_went_first
        FROM experiments
        WHERE id = ?
        """,
        (experiment_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"Experiment {experiment_id} not found")
    claim, pro_model, con_model, pro_went_first = row
    return claim, pro_model, con_model, bool(pro_went_first)


def fetch_judgments(cursor: sqlite3.Cursor, experiment_id: int) -> Dict[str, Dict[str, List[Optional[float]]]]:
    cursor.execute(
        """
        SELECT judge_model, turns_considered, score
        FROM judgments
        WHERE experiment_id = ?
        ORDER BY judge_model, turns_considered
        """,
        (experiment_id,),
    )
    rows = cursor.fetchall()
    if not rows:
        raise ValueError(f"No judgments recorded for experiment {experiment_id}")

    judge_data: Dict[str, Dict[str, List[Optional[float]]]] = {}
    for judge_model, turns, score in rows:
        judge_data.setdefault(judge_model, {"turns": [], "scores": []})
        judge_data[judge_model]["turns"].append(turns)
        judge_data[judge_model]["scores"].append(score)

    return judge_data


def create_single_debate_plot(experiment_id: int, output_filename: str) -> None:
    conn = sqlite3.connect("experiments.db")
    cursor = conn.cursor()

    try:
        claim, pro_model, con_model, pro_went_first = fetch_experiment(cursor, experiment_id)
        judge_data = fetch_judgments(cursor, experiment_id)
    finally:
        conn.close()

    unique_judges = {MODEL_LABELS.get(judge) for judge in judge_data.keys()}
    if len(judge_data.keys()) < 4:
        raise ValueError(
            f"Experiment {experiment_id} has judgments from fewer than four models: {sorted(unique_judges)}"
        )

    offsets = calculate_offsets(judge_data)

    fig, ax = plt.subplots(figsize=(8, 6))

    for judge_model in sorted(judge_data.keys()):
        data = judge_data[judge_model]
        turns = data["turns"]
        scores = data["scores"]
        color = MODEL_COLORS.get(judge_model, "#666666")
        label = MODEL_LABELS.get(judge_model, judge_model)

        points_with_offset = []
        for t, s in zip(turns, scores):
            adjusted = (5 if s is None else s) + offsets.get((judge_model, t), 0)
            points_with_offset.append(adjusted)

        for idx in range(len(turns) - 1):
            has_none = scores[idx] is None or scores[idx + 1] is None
            linestyle = "--" if has_none else "-"
            ax.plot(
                [turns[idx], turns[idx + 1]],
                [points_with_offset[idx], points_with_offset[idx + 1]],
                linestyle,
                color=color,
                linewidth=2,
                alpha=0.85,
            )

        for t, s in zip(turns, scores):
            offset = offsets.get((judge_model, t), 0)
            if s is None:
                ax.plot(
                    t,
                    5 + offset,
                    "o",
                    color=color,
                    markersize=6,
                    fillstyle="none",
                    markeredgewidth=1.5,
                    alpha=0.85,
                )
            else:
                ax.plot(t, s + offset, "o", color=color, markersize=6, alpha=0.85)

        ax.plot([], [], "o-", color=color, label=label, linewidth=2, markersize=6)

    pro_short = MODEL_LABELS.get(pro_model, pro_model)
    con_short = MODEL_LABELS.get(con_model, con_model)

    if pro_went_first:
        title = f"{pro_short} arguing Pro, then {con_short} arguing Con"
    else:
        title = f"{con_short} arguing Con, then {pro_short} arguing Pro"

    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xlabel("Debate Turn", fontsize=10)
    ax.set_ylabel("Score", fontsize=10)
    ax.set_xticks(range(1, 7))
    ax.set_ylim(0, 10)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=9)

    ax.text(
        0.02,
        0.95,
        "Supported",
        fontsize=9,
        alpha=0.7,
        style="italic",
        color=PRO_COLOR,
        fontweight="bold",
        transform=ax.transAxes,
    )
    ax.text(
        0.02,
        0.05,
        "Contradicted",
        fontsize=9,
        alpha=0.7,
        style="italic",
        color=CON_COLOR,
        fontweight="bold",
        transform=ax.transAxes,
    )

    note_text = (
        'Open circles denote "needs more evidence" rulings (plotted at score 5).\n'
        "Dashed lines connect segments involving those rulings."
    )
    fig.text(0.5, 0.01, note_text, fontsize=8, ha="center", va="bottom", style="italic", color="#666666")

    fig.suptitle(f"Debate #{experiment_id}: {claim}", fontsize=13, fontweight="bold", y=0.98)
    plt.savefig(output_filename, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved plot for experiment {experiment_id} to {output_filename}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a judge score plot for a single debate experiment.")
    parser.add_argument("experiment_id", type=int, help="Experiment ID to plot")
    parser.add_argument("output", type=str, help="Output image filename (e.g., single_debate_plot.png)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    create_single_debate_plot(args.experiment_id, args.output)
