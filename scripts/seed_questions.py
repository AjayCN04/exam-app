import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app import db  # noqa: E402

OPTION_COL_RE = re.compile(r"^option_(\d+)$")


def _load_from_json(path):
    with open(path) as f:
        raw = json.load(f)

    questions = []
    for q in raw:
        questions.append(
            {
                "question_text": q["question_text"],
                "points": q.get("points", 1),
                "options": q["options"],
                "correct_index": q["correct_index"],
            }
        )
    return questions, []


def _load_from_xlsx(path):
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.worksheets[0]

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return [], ["Sheet is empty."]

    header = [str(c).strip().lower() if c is not None else "" for c in rows[0]]
    col_index = {name: i for i, name in enumerate(header) if name}

    if "question_text" not in col_index:
        return [], ["Header row is missing a 'question_text' column."]
    if "correct_option" not in col_index:
        return [], ["Header row is missing a 'correct_option' column."]

    option_cols = sorted(
        (int(m.group(1)), i)
        for name, i in col_index.items()
        for m in [OPTION_COL_RE.match(name)]
        if m
    )
    if not option_cols:
        return [], ["Header row has no 'option_1', 'option_2', ... columns."]

    points_idx = col_index.get("points")

    questions = []
    errors = []
    for row_num, row in enumerate(rows[1:], start=2):
        if row is None or all(c is None or str(c).strip() == "" for c in row):
            continue  # skip blank rows

        question_text = row[col_index["question_text"]]
        question_text = str(question_text).strip() if question_text is not None else ""
        if not question_text:
            errors.append(f"Row {row_num}: 'question_text' is blank.")
            continue

        points_raw = row[points_idx] if points_idx is not None else None
        points = int(points_raw) if points_raw not in (None, "") else 1

        filled_options = []
        for col_num, idx in option_cols:
            text = row[idx] if idx < len(row) else None
            if text is not None and str(text).strip() != "":
                filled_options.append((col_num, str(text).strip()))

        if len(filled_options) < 2:
            errors.append(f"Row {row_num}: fewer than 2 non-blank options.")
            continue

        correct_raw = row[col_index["correct_option"]]
        try:
            correct_col = int(correct_raw)
        except (TypeError, ValueError):
            errors.append(f"Row {row_num}: 'correct_option' ({correct_raw!r}) is not a number.")
            continue

        matching = [i for i, (col_num, _) in enumerate(filled_options) if col_num == correct_col]
        if not matching:
            errors.append(
                f"Row {row_num}: correct_option={correct_col} does not match any "
                f"non-blank option column in this row."
            )
            continue

        questions.append(
            {
                "question_text": question_text,
                "points": points,
                "options": [text for _, text in filled_options],
                "correct_index": matching[0],
            }
        )

    return questions, errors


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/seed_questions.py <questions.json|questions.xlsx>")
        print(
            "JSON format: [{\"question_text\": \"...\", \"points\": 1, "
            "\"options\": [\"A\", \"B\"], \"correct_index\": 0}, ...]"
        )
        print(
            "XLSX format: header row with question_text, points (optional), "
            "option_1, option_2, ..., correct_option (1-based column number)"
        )
        sys.exit(1)

    path = sys.argv[1]
    ext = os.path.splitext(path)[1].lower()

    if ext == ".xlsx":
        questions, errors = _load_from_xlsx(path)
    elif ext == ".json":
        questions, errors = _load_from_json(path)
    else:
        print(f"Unsupported file type: {ext} (use .json or .xlsx)")
        sys.exit(1)

    if errors:
        print(f"Found {len(errors)} problem(s) — nothing was written to the database:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    if not questions:
        print("No questions found in the file.")
        sys.exit(1)

    for i, q in enumerate(questions):
        rs = db.execute(
            "INSERT INTO questions (question_text, points, order_index) VALUES (?, ?, ?)",
            [q["question_text"], q["points"], i],
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
