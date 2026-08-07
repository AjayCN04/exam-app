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
    # Denormalized copies of users.name / exams.title on exam_scores, kept in
    # sync with user renames going forward (see app/admin/users.py). Existing
    # rows are backfilled once here from the current users/exams data.
    added = False
    if _column_exists("exam_scores", "user_name"):
        print("exam_scores.user_name already exists — skipping add.")
    else:
        db.execute("ALTER TABLE exam_scores ADD COLUMN user_name TEXT")
        print("Added exam_scores.user_name.")
        added = True

    if _column_exists("exam_scores", "exam_name"):
        print("exam_scores.exam_name already exists — skipping add.")
    else:
        db.execute("ALTER TABLE exam_scores ADD COLUMN exam_name TEXT")
        print("Added exam_scores.exam_name.")
        added = True

    if added:
        db.execute(
            "UPDATE exam_scores SET user_name = (SELECT name FROM users WHERE id = exam_scores.user_id) "
            "WHERE user_name IS NULL"
        )
        db.execute(
            "UPDATE exam_scores SET exam_name = (SELECT title FROM exams WHERE id = exam_scores.exam_id) "
            "WHERE exam_name IS NULL"
        )
        print("Backfilled user_name/exam_name for existing exam_scores rows.")


if __name__ == "__main__":
    main()
    db.close_client()
