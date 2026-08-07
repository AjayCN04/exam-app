import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app import db  # noqa: E402


def main():
    if len(sys.argv) < 4:
        print(
            "Usage: python scripts/create_exam.py <exam_number> <title> <question_set_name> "
            "[max_attempts] [questions_per_module]"
        )
        print(
            "questions_per_module: omit (or 0) to use every question in the set; otherwise "
            "the exam picks that many questions from each module."
        )
        sys.exit(1)

    exam_number, title, set_name = sys.argv[1], sys.argv[2], sys.argv[3]
    max_attempts = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    questions_per_module = int(sys.argv[5]) if len(sys.argv) > 5 and int(sys.argv[5]) > 0 else None

    existing = db.execute("SELECT id FROM exams WHERE exam_number = ?", [exam_number])
    if existing.rows:
        print(f"Exam '{exam_number}' already exists (id={existing.rows[0][0]}) — skipping.")
        return

    set_rs = db.execute("SELECT id FROM question_sets WHERE name = ?", [set_name])
    if not set_rs.rows:
        print(f"No question set found named {set_name!r}.")
        sys.exit(1)
    set_id = set_rs.rows[0][0]

    rs = db.execute(
        """
        INSERT INTO exams (exam_number, title, set_id, start_time, end_time, max_attempts,
                            questions_per_module)
        VALUES (?, ?, ?, datetime('now'), datetime('now', '+30 days'), ?, ?)
        """,
        [exam_number, title, set_id, max_attempts, questions_per_module],
    )
    suffix = f", {questions_per_module} question(s)/module" if questions_per_module else ""
    print(f"Created exam '{title}' ({exam_number}), id={rs.last_insert_rowid}{suffix}.")


if __name__ == "__main__":
    main()
    db.close_client()
