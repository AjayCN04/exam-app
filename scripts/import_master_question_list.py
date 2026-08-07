import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app import db  # noqa: E402

DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "app",
    "exam_content",
    "Claude_Architect_Foundations_Master_Question_List.xlsx",
)

QUESTION_SET_NAME = "Claude Architect Foundations Master Question List"


def _load_rows(path):
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["Master Question List"] if "Master Question List" in wb.sheetnames else wb.worksheets[0]

    rows = list(ws.iter_rows(min_row=2, values_only=True))

    questions = []
    errors = []
    for row_num, row in enumerate(rows, start=2):
        if row is None or all(c is None or str(c).strip() == "" for c in row):
            continue

        module, question, c1, c2, c3, c4, correct_num, correct_desc, justification = row[:9]

        fields = {
            "Module": module,
            "Question": question,
            "Answer Choice 1": c1,
            "Answer Choice 2": c2,
            "Answer Choice 3": c3,
            "Answer Choice 4": c4,
            "Justification": justification,
        }
        for label, value in fields.items():
            if value is None or str(value).strip() == "":
                errors.append(f"Row {row_num}: '{label}' is blank.")

        choices = [c1, c2, c3, c4]
        try:
            correct_index = int(correct_num) - 1
        except (TypeError, ValueError):
            errors.append(f"Row {row_num}: 'Correct Choice Number' ({correct_num!r}) is not a number.")
            continue
        if not (0 <= correct_index <= 3):
            errors.append(f"Row {row_num}: 'Correct Choice Number' ({correct_num!r}) is not between 1 and 4.")
            continue

        if str(choices[correct_index]).strip() != str(correct_desc).strip():
            errors.append(
                f"Row {row_num}: 'Correct Choice' text does not match Answer Choice {correct_index + 1}."
            )
            continue

        questions.append(
            {
                "module": str(module).strip(),
                "question_text": str(question).strip(),
                "options": [str(c).strip() for c in choices],
                "correct_index": correct_index,
                "justification": str(justification).strip(),
            }
        )

    return questions, errors


def _get_or_create_question_set(name):
    rs = db.execute("SELECT id FROM question_sets WHERE name = ?", [name])
    if rs.rows:
        return rs.rows[0][0]
    rs = db.execute("INSERT INTO question_sets (name) VALUES (?)", [name])
    return rs.last_insert_rowid


def _get_or_create_module(name, order_index, cache):
    if name in cache:
        return cache[name]
    rs = db.execute("SELECT id FROM exam_modules WHERE name = ?", [name])
    if rs.rows:
        module_id = rs.rows[0][0]
    else:
        rs = db.execute(
            "INSERT INTO exam_modules (name, order_index) VALUES (?, ?)",
            [name, order_index],
        )
        module_id = rs.last_insert_rowid
    cache[name] = module_id
    return module_id


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH

    questions, errors = _load_rows(path)

    if errors:
        print(f"Found {len(errors)} problem(s) — nothing was written to the database:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    if not questions:
        print("No questions found in the file.")
        sys.exit(1)

    set_id = _get_or_create_question_set(QUESTION_SET_NAME)

    module_cache = {}
    module_order = 0
    option_count = 0
    for i, q in enumerate(questions):
        if q["module"] not in module_cache:
            module_id = _get_or_create_module(q["module"], module_order, module_cache)
            module_order += 1
        else:
            module_id = module_cache[q["module"]]

        rs = db.execute(
            "INSERT INTO questions (set_id, module_id, question_text, points, order_index) "
            "VALUES (?, ?, ?, ?, ?)",
            [set_id, module_id, q["question_text"], 3, i],
        )
        question_id = rs.last_insert_rowid

        option_ids = []
        for j, opt_text in enumerate(q["options"]):
            rs = db.execute(
                "INSERT INTO options (question_id, option_text, order_index) VALUES (?, ?, ?)",
                [question_id, opt_text, j],
            )
            option_ids.append(rs.last_insert_rowid)
            option_count += 1

        correct_option_id = option_ids[q["correct_index"]]
        db.execute(
            "INSERT INTO answer_key (question_id, correct_option_id, justification) "
            "VALUES (?, ?, ?)",
            [question_id, correct_option_id, q["justification"]],
        )

    print(
        f"Seeded 1 question set, {len(module_cache)} modules, {len(questions)} questions, "
        f"{option_count} options, {len(questions)} answer-key rows."
    )


if __name__ == "__main__":
    main()
    db.close_client()
