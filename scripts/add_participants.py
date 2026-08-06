import csv
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
        print("Usage: python scripts/add_participants.py <input_csv> <output_csv>")
        print("Input CSV must have a header row: name,email")
        sys.exit(1)

    input_path, output_path = sys.argv[1], sys.argv[2]

    with open(input_path, newline="") as infile, open(output_path, "w", newline="") as outfile:
        reader = csv.DictReader(infile)
        writer = csv.writer(outfile)
        writer.writerow(["name", "email", "link"])
        count = 0
        for row in reader:
            name = row["name"].strip()
            email = (row.get("email") or "").strip()
            token = secrets.token_urlsafe(32)
            db.execute(
                "INSERT INTO participants (name, email, access_token) VALUES (?, ?, ?)",
                [name, email or None, token],
            )
            writer.writerow([name, email, f"{BASE_URL}/exam/{token}"])
            count += 1

    print(f"Added {count} participants. Links written to {output_path}")


if __name__ == "__main__":
    main()
    db.close_client()
