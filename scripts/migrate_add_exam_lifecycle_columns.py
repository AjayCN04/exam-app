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
    if _column_exists("exams", "is_closed"):
        print("exams.is_closed already exists — skipping.")
    else:
        db.execute("ALTER TABLE exams ADD COLUMN is_closed INTEGER NOT NULL DEFAULT 0")
        print("Added exams.is_closed.")

    if _column_exists("exams", "is_active"):
        print("exams.is_active already exists — skipping.")
    else:
        db.execute("ALTER TABLE exams ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
        print("Added exams.is_active (existing rows backfilled to 1).")


if __name__ == "__main__":
    main()
    db.close_client()
