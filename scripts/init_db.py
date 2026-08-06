import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app import db  # noqa: E402


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    schema_path = os.path.join(project_root, "schema.sql")
    with open(schema_path) as f:
        sql = f.read()

    statements = [s.strip() for s in sql.split(";") if s.strip()]
    for stmt in statements:
        db.execute(stmt)

    print(f"Applied {len(statements)} statements to the database.")


if __name__ == "__main__":
    main()
    db.close_client()
