import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app import db  # noqa: E402

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")

QUESTIONS = [
    {
        "question_text": "What is the capital of France?",
        "options": ["Paris", "London", "Berlin", "Madrid"],
        "correct_index": 0,
    },
    {
        "question_text": "Which of these is a Python web framework?",
        "options": ["Flask", "Photoshop", "Excel", "Figma"],
        "correct_index": 0,
    },
    {
        "question_text": "2 + 2 = ?",
        "options": ["3", "4", "5", "22"],
        "correct_index": 1,
    },
]

PARTICIPANTS = ["Test User One", "Test User Two"]


def main():
    for i, q in enumerate(QUESTIONS):
        rs = db.execute(
            "INSERT INTO questions (question_text, points, order_index) VALUES (?, ?, ?)",
            [q["question_text"], 1, i],
        )
        question_id = rs.last_insert_rowid
        for j, opt_text in enumerate(q["options"]):
            db.execute(
                "INSERT INTO options (question_id, option_text, is_correct, order_index) "
                "VALUES (?, ?, ?, ?)",
                [question_id, opt_text, 1 if j == q["correct_index"] else 0, j],
            )

    print("Seeded questions. Test participant links:")
    for name in PARTICIPANTS:
        token = secrets.token_urlsafe(32)
        db.execute(
            "INSERT INTO participants (name, access_token) VALUES (?, ?)",
            [name, token],
        )
        print(f"  {name}: {BASE_URL}/exam/{token}")


if __name__ == "__main__":
    main()
    db.close_client()
