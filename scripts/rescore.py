import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app import db  # noqa: E402


def main():
    attempts_rs = db.execute("SELECT id FROM attempts WHERE submitted_at IS NOT NULL")

    for attempt_row in attempts_rs.rows:
        attempt_id = attempt_row.asdict()["id"]

        ans_rs = db.execute(
            """
            SELECT ans.id AS answer_id, ans.selected_option_id, q.points
            FROM answers ans
            JOIN questions q ON q.id = ans.question_id
            WHERE ans.attempt_id = ?
            """,
            [attempt_id],
        )

        total_score = 0
        for a_row in ans_rs.rows:
            a = a_row.asdict()
            is_correct = False
            if a["selected_option_id"] is not None:
                opt_rs = db.execute(
                    "SELECT is_correct FROM options WHERE id = ?", [a["selected_option_id"]]
                )
                is_correct = bool(opt_rs.rows and opt_rs.rows[0].asdict()["is_correct"])
            if is_correct:
                total_score += a["points"]
            db.execute(
                "UPDATE answers SET is_correct = ? WHERE id = ?",
                [1 if is_correct else 0, a["answer_id"]],
            )

        db.execute("UPDATE attempts SET total_score = ? WHERE id = ?", [total_score, attempt_id])

    print(f"Rescored {len(attempts_rs.rows)} submitted attempts.")


if __name__ == "__main__":
    main()
    db.close_client()
