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
    if _column_exists("exams", "questions_per_module"):
        print("exams.questions_per_module already exists — skipping.")
    else:
        db.execute("ALTER TABLE exams ADD COLUMN questions_per_module INTEGER")
        print("Added exams.questions_per_module (NULL = use the full question set).")


if __name__ == "__main__":
    main()
    db.close_client()
