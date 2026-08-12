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
    # questions.is_multi_select flags whether a question allows more than one
    # correct answer (rendered as checkboxes instead of radio buttons).
    if _column_exists("questions", "is_multi_select"):
        print("questions.is_multi_select already exists — skipping add.")
    else:
        db.execute(
            "ALTER TABLE questions ADD COLUMN is_multi_select INTEGER NOT NULL DEFAULT 0"
        )
        print("Added questions.is_multi_select.")

    # options.is_correct becomes the authoritative per-option correctness
    # flag going forward (supports 1..N correct options per question).
    # answer_key.correct_option_id is left as-is for schema compatibility —
    # for multi-select questions it will only hold one of several correct
    # option ids and is no longer treated as authoritative anywhere.
    if _column_exists("options", "is_correct"):
        print("options.is_correct already exists — skipping add.")
    else:
        db.execute("ALTER TABLE options ADD COLUMN is_correct INTEGER NOT NULL DEFAULT 0")
        print("Added options.is_correct.")
        db.execute(
            "UPDATE options SET is_correct = 1 "
            "WHERE id IN (SELECT correct_option_id FROM answer_key)"
        )
        print("Backfilled options.is_correct from existing answer_key data.")

    # attempt_answers.selected_option_ids holds a comma-joined list of
    # selected option ids, populated for every question going forward
    # (single- or multi-select). The legacy selected_option_id scalar
    # column keeps being populated for single-select answers too. Rows
    # predating this migration have selected_option_ids IS NULL — reads
    # must fall back to selected_option_id in that case.
    if _column_exists("attempt_answers", "selected_option_ids"):
        print("attempt_answers.selected_option_ids already exists — skipping add.")
    else:
        db.execute("ALTER TABLE attempt_answers ADD COLUMN selected_option_ids TEXT")
        print("Added attempt_answers.selected_option_ids.")


if __name__ == "__main__":
    main()
    db.close_client()
