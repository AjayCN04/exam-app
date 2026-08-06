import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app import db  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/seed_questions.py <questions.json>")
        print(
            'Format: [{"question_text": "...", "points": 1, '
            '"options": ["A", "B"], "correct_index": 0}, ...]'
        )
        sys.exit(1)

    with open(sys.argv[1]) as f:
        questions = json.load(f)

    for i, q in enumerate(questions):
        rs = db.execute(
            "INSERT INTO questions (question_text, points, order_index) VALUES (?, ?, ?)",
            [q["question_text"], q.get("points", 1), i],
        )
        question_id = rs.last_insert_rowid
        for j, opt_text in enumerate(q["options"]):
            db.execute(
                "INSERT INTO options (question_id, option_text, is_correct, order_index) "
                "VALUES (?, ?, ?, ?)",
                [question_id, opt_text, 1 if j == q["correct_index"] else 0, j],
            )

    print(f"Seeded {len(questions)} questions.")


if __name__ == "__main__":
    main()
    db.close_client()
