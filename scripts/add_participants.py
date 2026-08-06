import csv
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app import db  # noqa: E402

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000")


def _read_from_csv(path):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return [{"name": row.get("name"), "email": row.get("email")} for row in reader]


def _read_from_xlsx(path):
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.worksheets[0]

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    header = [str(c).strip().lower() if c is not None else "" for c in rows[0]]
    col_index = {name: i for i, name in enumerate(header) if name}

    if "name" not in col_index:
        raise ValueError("Header row is missing a 'name' column.")
    email_idx = col_index.get("email")

    result = []
    for row in rows[1:]:
        if row is None or all(c is None or str(c).strip() == "" for c in row):
            continue  # skip blank rows
        name = row[col_index["name"]]
        email = row[email_idx] if email_idx is not None else None
        result.append(
            {
                "name": str(name).strip() if name is not None else "",
                "email": str(email).strip() if email is not None else "",
            }
        )
    return result


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/add_participants.py <input.csv|input.xlsx> <output_csv>")
        print("Input file must have a header row: name,email (email optional)")
        sys.exit(1)

    input_path, output_path = sys.argv[1], sys.argv[2]
    ext = os.path.splitext(input_path)[1].lower()

    if ext == ".xlsx":
        rows = _read_from_xlsx(input_path)
    elif ext == ".csv":
        rows = _read_from_csv(input_path)
    else:
        print(f"Unsupported file type: {ext} (use .csv or .xlsx)")
        sys.exit(1)

    errors = []
    for row_num, row in enumerate(rows, start=2):
        if not (row.get("name") or "").strip():
            errors.append(f"Row {row_num}: 'name' is blank.")

    if errors:
        print(f"Found {len(errors)} problem(s) — no participants were added:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    if not rows:
        print("No participant rows found in the file.")
        sys.exit(1)

    with open(output_path, "w", newline="") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["name", "email", "link"])
        for row in rows:
            name = row["name"].strip()
            email = (row.get("email") or "").strip()
            token = secrets.token_urlsafe(32)
            db.execute(
                "INSERT INTO participants (name, email, access_token) VALUES (?, ?, ?)",
                [name, email or None, token],
            )
            writer.writerow([name, email, f"{BASE_URL}/exam/{token}"])

    print(f"Added {len(rows)} participants. Links written to {output_path}")


if __name__ == "__main__":
    main()
    db.close_client()
