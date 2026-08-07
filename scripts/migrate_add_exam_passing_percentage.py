import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app import db  # noqa: E402


def _column_exists(table, column):
    rs = db.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in rs.rows)


def main():
    # exams.passing_percentage was previously added (migrate_add_exam_scores.py)
    # and then dropped (migrate_apply_scoring_rules.py) in favor of a single
    # global env var. This re-adds it as a per-exam override: NULL means
    # "use the global PASSING_PERCENTAGE env var", matching every exam's
    # current behavior until an admin sets one explicitly.
    if _column_exists("exams", "passing_percentage"):
        print("exams.passing_percentage already exists — skipping.")
    else:
        db.execute("ALTER TABLE exams ADD COLUMN passing_percentage REAL")
        print("Added exams.passing_percentage (NULL = use the global PASSING_PERCENTAGE env var).")


if __name__ == "__main__":
    main()
    db.close_client()
