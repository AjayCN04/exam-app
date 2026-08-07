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
    rs = db.execute("UPDATE questions SET points = 3 WHERE points != 3")
    print(f"Updated points to 3 on {rs.rows_affected} question(s).")

    if _column_exists("exams", "passing_percentage"):
        db.execute("ALTER TABLE exams DROP COLUMN passing_percentage")
        print("Dropped exams.passing_percentage.")
    else:
        print("exams.passing_percentage already removed — skipping.")


if __name__ == "__main__":
    main()
    db.close_client()
