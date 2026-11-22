"""Owner-only fixture provisioning for a fresh local demonstration database."""

import os
import secrets
import psycopg
from werkzeug.security import generate_password_hash


def provision(conn):
    credentials = []
    for role, identity, status, name in [
        ("admin", None, "active", "office"),
        ("student", 1, "active", "riya"),
        ("teacher", 1, "active", "mira"),
        ("teacher", 4, "active", "sami"),
        ("student", 2, "pending", "ayan"),
        ("student", 20, "disabled", "rehan"),
    ]:
        password = secrets.token_urlsafe(18)
        email = name + "@courselink.example"
        conn.execute(
            """INSERT INTO users(email,password_hash,role,status,student_id,teacher_id)
            VALUES(%s,%s,%s,%s,%s,%s)""",
            (
                email,
                generate_password_hash(password),
                role,
                status,
                identity if role == "student" else None,
                identity if role == "teacher" else None,
            ),
        )
        credentials.append(f"{role:8} {status:9} {email:29} {password}")
    return credentials


if __name__ == "__main__":
    with psycopg.connect(os.environ["OWNER_DATABASE_URL"]) as connection:
        credentials = provision(connection)
    print("\n".join(credentials))
