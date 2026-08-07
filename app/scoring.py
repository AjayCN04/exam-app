import os


def get_passing_percentage():
    raw = os.environ.get("PASSING_PERCENTAGE")
    if raw is None:
        raise RuntimeError("PASSING_PERCENTAGE is not set in the environment.")
    try:
        return float(raw)
    except ValueError:
        raise RuntimeError(f"PASSING_PERCENTAGE ({raw!r}) is not a number.") from None


def score_attempt(answers):
    """answers: iterable of (is_correct, points) pairs, one per question in the attempt."""
    answers = list(answers)
    score = sum(points for is_correct, points in answers if is_correct)
    max_score = sum(points for _, points in answers)
    percentage = (score / max_score * 100) if max_score else 0.0
    passed = percentage >= get_passing_percentage()
    return {
        "score": score,
        "max_score": max_score,
        "percentage": percentage,
        "passed": passed,
    }
