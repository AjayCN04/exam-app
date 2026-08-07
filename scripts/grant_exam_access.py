import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app import db  # noqa: E402

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/grant_exam_access.py <exam_number> <email> [email2 ...]")
        sys.exit(1)

    exam_number, emails = sys.argv[1], sys.argv[2:]

    exam_rs = db.execute("SELECT id FROM exams WHERE exam_number = ?", [exam_number])
    if not exam_rs.rows:
        print(f"No exam found with exam_number {exam_number!r}.")
        sys.exit(1)
    exam_id = exam_rs.rows[0][0]

    for email in emails:
        user_rs = db.execute("SELECT id, name FROM users WHERE email = ?", [email])
        if not user_rs.rows:
            print(f"Skipping {email}: no matching user.")
            continue
        user_id, name = user_rs.rows[0][0], user_rs.rows[0][1]

        existing = db.execute(
            "SELECT access_token FROM exam_access WHERE user_id = ? AND exam_id = ?",
            [user_id, exam_id],
        )
        if existing.rows:
            token = existing.rows[0][0]
            print(f"{name} <{email}> already has access: {BASE_URL}/exam/{token}")
            continue

        token = secrets.token_urlsafe(32)
        db.execute(
            "INSERT INTO exam_access (user_id, exam_id, access_token) VALUES (?, ?, ?)",
            [user_id, exam_id, token],
        )
        print(f"{name} <{email}>: {BASE_URL}/exam/{token}")


if __name__ == "__main__":
    main()
    db.close_client()
