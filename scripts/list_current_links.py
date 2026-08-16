"""Print every active participant's exam link and status, using the current
public URL (from .run/public_url.txt if present, else BASE_URL, else localhost).

Usage: .venv/bin/python scripts/list_current_links.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app import db  # noqa: E402


def _base_url():
    run_dir_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".run", "public_url.txt")
    if os.path.exists(run_dir_file):
        with open(run_dir_file) as f:
            url = f.read().strip()
            if url:
                return url
    return os.environ.get("BASE_URL", "http://127.0.0.1:5000")


def main():
    base_url = _base_url()
    rows = db.execute(
        """
        SELECT u.name, u.email, e.exam_number, e.title, ea.access_token,
               CASE WHEN att.submitted_at IS NOT NULL THEN 'completed'
                    WHEN att.id IS NOT NULL THEN 'in progress'
                    ELSE 'not started' END
        FROM exam_access ea
        JOIN users u ON u.id = ea.user_id
        JOIN exams e ON e.id = ea.exam_id
        LEFT JOIN exam_attempts att ON att.id = (
            SELECT id FROM exam_attempts
            WHERE exam_access_id = ea.id
            ORDER BY attempt_number DESC LIMIT 1
        )
        WHERE u.is_active = 1
        ORDER BY e.exam_number, u.name
        """
    ).rows

    print(f"Base URL: {base_url}\n")
    for name, email, exam_number, title, token, status in rows:
        print(f"{name} <{email}> — {title} ({exam_number}) — {status}")
        print(f"  {base_url}/exam/{token}\n")

    db.close_client()


if __name__ == "__main__":
    main()
