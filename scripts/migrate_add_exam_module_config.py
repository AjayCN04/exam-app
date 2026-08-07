import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app import db  # noqa: E402


def _table_exists(table):
    rs = db.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", [table])
    return bool(rs.rows)


def main():
    # One row per module included in an exam, with that module's question
    # count. A module with no row for a given exam simply wasn't selected.
    # This table is only ever populated for exams created through the admin
    # UI going forward — existing exams keep using the legacy global
    # exams.questions_per_module column, so this migration must NEVER
    # backfill rows for exams that already exist.
    if _table_exists("exam_module_config"):
        print("exam_module_config already exists — skipping.")
    else:
        db.execute(
            """
            CREATE TABLE exam_module_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_id INTEGER NOT NULL REFERENCES exams(id),
                module_id INTEGER NOT NULL REFERENCES exam_modules(id),
                question_count INTEGER NOT NULL,
                UNIQUE (exam_id, module_id)
            )
            """
        )
        db.execute(
            "CREATE INDEX idx_exam_module_config_exam_id ON exam_module_config(exam_id)"
        )
        print("Created exam_module_config and its index.")


if __name__ == "__main__":
    main()
    db.close_client()
