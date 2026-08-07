from .. import db


def active_users():
    rs = db.execute("SELECT id, name, email FROM users WHERE is_active = 1 ORDER BY name")
    return [r.asdict() for r in rs.rows]


def archived_users():
    rs = db.execute("SELECT id, name, email FROM users WHERE is_active = 0 ORDER BY name")
    return [r.asdict() for r in rs.rows]


def list_exams_with_status():
    """Status is computed in SQL against the DB's own clock (datetime('now'))
    rather than in Python, so it can't drift from whatever clock start_time/
    end_time were originally written against."""
    rs = db.execute(
        """
        SELECT id, exam_number, title, start_time, end_time,
               CASE
                   WHEN datetime('now') < start_time THEN 'upcoming'
                   WHEN datetime('now') > end_time THEN 'completed'
                   ELSE 'active'
               END AS status
        FROM exams
        ORDER BY created_at DESC
        """
    )
    return [r.asdict() for r in rs.rows]


def results_rows(exam_id):
    rs = db.execute(
        """
        SELECT ea.id, u.name, u.email, eat.started_at, eat.submitted_at, eat.total_score,
               es.passed
        FROM exam_access ea
        JOIN users u ON u.id = ea.user_id
        LEFT JOIN exam_attempts eat ON eat.exam_access_id = ea.id AND eat.attempt_number = 1
        LEFT JOIN exam_scores es ON es.exam_attempt_id = eat.id
        WHERE ea.exam_id = ?
        ORDER BY u.name
        """,
        [exam_id],
    )
    rows = []
    for row in rs.rows:
        r = row.asdict()
        if r["submitted_at"]:
            r["status"] = "completed"
        elif r["started_at"]:
            r["status"] = "in_progress"
        else:
            r["status"] = "not_started"

        if r["passed"] is None:
            r["result"] = ""
        elif r["passed"]:
            r["result"] = "Pass"
        else:
            r["result"] = "Fail"
        rows.append(r)
    return rows
