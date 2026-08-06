import os
import sys

import openpyxl

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(PROJECT_ROOT, "content")


def make_questions_template(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Questions"
    ws.append(["question_text", "points", "option_1", "option_2", "option_3", "option_4", "correct_option"])
    ws.append(["What is the capital of France?", 1, "Paris", "London", "Berlin", "Madrid", 1])
    wb.save(path)


def make_participants_template(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Participants"
    ws.append(["name", "email"])
    ws.append(["Jane Doe", "jane.doe@example.com"])
    wb.save(path)


def main():
    os.makedirs(CONTENT_DIR, exist_ok=True)

    q_path = os.path.join(CONTENT_DIR, "questions_template.xlsx")
    p_path = os.path.join(CONTENT_DIR, "participants_template.xlsx")

    for path, make in [(q_path, make_questions_template), (p_path, make_participants_template)]:
        if os.path.exists(path):
            print(f"Skipping {path} (already exists)")
            continue
        make(path)
        print(f"Created {path}")

    print(
        "\nFill in the sheets, then run:\n"
        "  python scripts/seed_questions.py content/questions_template.xlsx\n"
        "  python scripts/add_participants.py content/participants_template.xlsx content/links.csv"
    )


if __name__ == "__main__":
    main()
