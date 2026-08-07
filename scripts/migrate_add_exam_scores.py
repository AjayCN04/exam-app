import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app import db  # noqa: E402


def _column_exists(table, column):
    rs = db.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in rs.rows)


def _table_exists(table):
    rs = db.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", [table])
    return bool(rs.rows)


def main():
    if _column_exists("exams", "passing_percentage"):
        print("exams.passing_percentage already exists — skipping.")
    else:
        db.execute("ALTER TABLE exams ADD COLUMN passing_percentage REAL")
        print("Added exams.passing_percentage.")

    if _table_exists("exam_scores"):
        print("exam_scores already exists — skipping.")
    else:
        db.execute(
            """
            CREATE TABLE exam_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_attempt_id INTEGER NOT NULL UNIQUE REFERENCES exam_attempts(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                exam_id INTEGER NOT NULL REFERENCES exams(id),
                attempt_number INTEGER NOT NULL,
                score INTEGER NOT NULL,
                max_score INTEGER NOT NULL,
                percentage REAL NOT NULL,
                passed INTEGER,
                scored_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        db.execute("CREATE INDEX idx_exam_scores_user_id ON exam_scores(user_id)")
        db.execute("CREATE INDEX idx_exam_scores_exam_id ON exam_scores(exam_id)")
        db.execute("CREATE INDEX idx_exam_scores_user_exam ON exam_scores(user_id, exam_id)")
        print("Created exam_scores and its indexes.")


if __name__ == "__main__":
    main()
    db.close_client()
