#!/usr/bin/env python3
"""
Storage layer for debate experiments.

Provides an abstraction over experiment storage with SQLite implementation.
"""

import sqlite3
import json
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime


class ExperimentStore(ABC):
    """Abstract base class for experiment storage."""

    @abstractmethod
    def save(self, experiment: Dict[str, Any]) -> int:
        """
        Save an experiment and return its ID.

        Args:
            experiment: Experiment data dictionary

        Returns:
            Experiment ID
        """
        pass

    @abstractmethod
    def get_by_id(self, experiment_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve an experiment by ID.

        Args:
            experiment_id: ID of the experiment

        Returns:
            Experiment dictionary or None if not found
        """
        pass

    @abstractmethod
    def query(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query experiments with optional filters.

        Args:
            filters: Dictionary of filter criteria (topic, verdict, min_score, etc.)

        Returns:
            List of experiment dictionaries
        """
        pass

    @abstractmethod
    def get_all(self) -> List[Dict[str, Any]]:
        """
        Get all experiments.

        Returns:
            List of experiment dictionaries
        """
        pass


class SQLiteExperimentStore(ExperimentStore):
    """SQLite implementation of experiment storage."""

    def __init__(self, db_path: str = "experiments.db"):
        """
        Initialize SQLite store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main experiments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim TEXT NOT NULL,
                claim_id TEXT,
                topic TEXT,
                timestamp TEXT NOT NULL,

                -- Models used
                pro_model TEXT NOT NULL,
                con_model TEXT NOT NULL,
                judge_model TEXT NOT NULL,

                -- Configuration
                turns INTEGER NOT NULL,
                pro_went_first INTEGER NOT NULL,

                -- Ground truth
                gt_verdict TEXT,
                gt_source TEXT,
                gt_url TEXT,

                -- Judge decision
                judge_verdict TEXT NOT NULL,
                judge_score INTEGER NOT NULL,
                judge_reasoning TEXT NOT NULL,

                -- Full data as JSON blob for complex queries
                full_data TEXT NOT NULL,

                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Index for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_topic ON experiments(topic)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_judge_verdict ON experiments(judge_verdict)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_judge_score ON experiments(judge_score)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON experiments(timestamp)
        """)

        # Debate turns table (normalized for easy querying)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS debate_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER NOT NULL,
                turn_number INTEGER NOT NULL,
                debater TEXT NOT NULL,
                argument TEXT NOT NULL,
                source_url TEXT NOT NULL,
                source_quote TEXT NOT NULL,
                refused INTEGER NOT NULL DEFAULT 0,
                refusal_reason TEXT,
                FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_experiment_id ON debate_turns(experiment_id)
        """)

        conn.commit()
        conn.close()

    def save(self, experiment: Dict[str, Any]) -> int:
        """Save an experiment to SQLite."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Extract fields for main table
        claim_data = experiment.get("claim_data", {})
        ground_truth = experiment.get("ground_truth", {})
        config = experiment.get("experiment_config", {})
        models = config.get("models", {})
        judge_decision = experiment.get("judge_decision", {})

        cursor.execute("""
            INSERT INTO experiments (
                claim, claim_id, topic, timestamp,
                pro_model, con_model, judge_model,
                turns, pro_went_first,
                gt_verdict, gt_source, gt_url,
                judge_verdict, judge_score, judge_reasoning,
                full_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            claim_data.get("claim", ""),
            claim_data.get("claim_id"),
            claim_data.get("topic"),
            config.get("timestamp", ""),
            models.get("pro", ""),
            models.get("con", ""),
            models.get("judge", ""),
            config.get("turns", 0),
            1 if config.get("pro_went_first", True) else 0,
            ground_truth.get("verdict"),
            ground_truth.get("source"),
            ground_truth.get("url"),
            judge_decision.get("verdict", ""),
            judge_decision.get("score", 0),
            judge_decision.get("reasoning", ""),
            json.dumps(experiment)
        ))

        experiment_id = cursor.lastrowid

        # Save debate turns
        for turn in experiment.get("debate_transcript", []):
            cursor.execute("""
                INSERT INTO debate_turns (
                    experiment_id, turn_number, debater,
                    argument, source_url, source_quote,
                    refused, refusal_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                experiment_id,
                turn.get("turn", 0),
                turn.get("debater", ""),
                turn.get("argument", ""),
                turn.get("source_url", ""),
                turn.get("source_quote", ""),
                1 if turn.get("refused", False) else 0,
                turn.get("refusal_reason")
            ))

        conn.commit()
        conn.close()

        return experiment_id

    def get_by_id(self, experiment_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve an experiment by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT full_data FROM experiments WHERE id = ?", (experiment_id,))
        row = cursor.fetchone()

        conn.close()

        if row:
            return json.loads(row[0])
        return None

    def query(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Query experiments with filters."""
        if filters is None:
            filters = {}

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build WHERE clause
        where_clauses = []
        params = []

        if "topic" in filters:
            where_clauses.append("topic = ?")
            params.append(filters["topic"])

        if "judge_verdict" in filters:
            where_clauses.append("judge_verdict = ?")
            params.append(filters["judge_verdict"])

        if "min_score" in filters:
            where_clauses.append("judge_score >= ?")
            params.append(filters["min_score"])

        if "max_score" in filters:
            where_clauses.append("judge_score <= ?")
            params.append(filters["max_score"])

        if "pro_model" in filters:
            where_clauses.append("pro_model = ?")
            params.append(filters["pro_model"])

        if "con_model" in filters:
            where_clauses.append("con_model = ?")
            params.append(filters["con_model"])

        if "judge_model" in filters:
            where_clauses.append("judge_model = ?")
            params.append(filters["judge_model"])

        if "gt_verdict" in filters:
            where_clauses.append("gt_verdict = ?")
            params.append(filters["gt_verdict"])

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        query = f"SELECT full_data FROM experiments WHERE {where_clause} ORDER BY timestamp DESC"
        cursor.execute(query, params)

        experiments = [json.loads(row[0]) for row in cursor.fetchall()]

        conn.close()
        return experiments

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all experiments."""
        return self.query()

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics about experiments."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        stats = {}

        # Total count
        cursor.execute("SELECT COUNT(*) FROM experiments")
        stats["total_experiments"] = cursor.fetchone()[0]

        # Count by verdict
        cursor.execute("""
            SELECT judge_verdict, COUNT(*)
            FROM experiments
            GROUP BY judge_verdict
        """)
        stats["by_verdict"] = dict(cursor.fetchall())

        # Count by topic
        cursor.execute("""
            SELECT topic, COUNT(*)
            FROM experiments
            WHERE topic IS NOT NULL
            GROUP BY topic
        """)
        stats["by_topic"] = dict(cursor.fetchall())

        # Average score
        cursor.execute("SELECT AVG(judge_score) FROM experiments WHERE judge_score >= 0")
        avg_score = cursor.fetchone()[0]
        stats["average_score"] = round(avg_score, 2) if avg_score is not None else None

        # Score distribution
        cursor.execute("""
            SELECT
                CASE
                    WHEN judge_score = -1 THEN 'needs_evidence'
                    WHEN judge_score <= 4 THEN 'contradicted'
                    WHEN judge_score = 5 THEN 'ambiguous'
                    ELSE 'supported'
                END as category,
                COUNT(*)
            FROM experiments
            GROUP BY category
        """)
        stats["score_distribution"] = dict(cursor.fetchall())

        conn.close()
        return stats
