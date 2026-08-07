import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app import db  # noqa: E402

DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content", "Users.xlsx"
)


def _load_users(path):
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.worksheets[0]

    rows = list(ws.iter_rows(min_row=2, values_only=True))

    users = []
    errors = []
    seen_emails = {}
    for row_num, row in enumerate(rows, start=2):
        if row is None or all(c is None or str(c).strip() == "" for c in row):
            continue

        name, email = row[0], row[1]
        name = str(name).strip() if name is not None else ""
        email = str(email).strip() if email is not None else ""

        if not name:
            errors.append(f"Row {row_num}: 'Name' is blank.")
            continue
        if not email:
            errors.append(f"Row {row_num}: 'Email ID' is blank.")
            continue

        key = email.lower()
        if key in seen_emails:
            print(f"Skipping row {row_num}: duplicate of row {seen_emails[key]} (email={email}).")
            continue
        seen_emails[key] = row_num

        users.append({"name": name, "email": email})

    return users, errors


def _get_or_create_user(name, email):
    rs = db.execute("SELECT id FROM users WHERE email = ?", [email])
    if rs.rows:
        return rs.rows[0][0], False
    rs = db.execute("INSERT INTO users (name, email) VALUES (?, ?)", [name, email])
    return rs.last_insert_rowid, True


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH

    users, errors = _load_users(path)

    if errors:
        print(f"Found {len(errors)} problem(s) — nothing was written to the database:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    if not users:
        print("No users found in the file.")
        sys.exit(1)

    inserted = 0
    skipped_existing = 0
    for u in users:
        _, created = _get_or_create_user(u["name"], u["email"])
        if created:
            inserted += 1
        else:
            skipped_existing += 1

    print(f"Inserted {inserted} new user(s); {skipped_existing} already existed by email.")


if __name__ == "__main__":
    main()
    db.close_client()
