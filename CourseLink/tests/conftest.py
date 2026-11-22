"""Each test owns a fresh disposable database, including independent HTTP connections."""

import os
import secrets
from pathlib import Path
import pytest
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from werkzeug.security import generate_password_hash
from app import create_app

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def cluster():
    owner = conninfo_to_dict(os.environ["TEST_OWNER_URL"])
    web = conninfo_to_dict(os.environ["TEST_DATABASE_URL"])
    assert owner["dbname"].endswith("_test") and web["dbname"] == owner["dbname"]
    assert web["user"] == "courselink_web"
    catalog = make_conninfo(**owner)
    template = "cl_test_template_" + secrets.token_hex(5)
    with psycopg.connect(catalog, autocommit=True) as c:
        c.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(template)))
    try:
        with psycopg.connect(make_conninfo(**(owner | {"dbname": template}))) as c:
            for file in ("courselink.sql", "permissions.sql"):
                c.execute((ROOT / "database" / file).read_text(encoding="utf8"))
        yield owner, web, template
    finally:
        with psycopg.connect(catalog, autocommit=True) as c:
            c.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(template)))


@pytest.fixture
def urls(cluster):
    owner, web, template = cluster
    name = "cl_test_" + secrets.token_hex(6)
    with psycopg.connect(make_conninfo(**owner), autocommit=True) as c:
        c.execute(
            sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(
                sql.Identifier(name), sql.Identifier(template)
            )
        )
    try:
        yield tuple(
            make_conninfo(**(config | {"dbname": name})) for config in (owner, web)
        )
    finally:
        with psycopg.connect(make_conninfo(**owner), autocommit=True) as c:
            c.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


@pytest.fixture
def conn(urls):
    with psycopg.connect(urls[0], autocommit=True) as c:
        yield c


@pytest.fixture
def client(urls):
    app = create_app(
        dict(
            TESTING=True,
            SECRET_KEY=secrets.token_hex(32),
            DATABASE_URL=urls[1],
            WTF_CSRF_ENABLED=False,
        )
    )
    return app.test_client()


@pytest.fixture
def identity(conn, client):
    def create(role="student", who=1, state="active", signin=True):
        email = secrets.token_hex(5) + "@example.org"
        password = secrets.token_urlsafe(20)
        uid = conn.execute(
            """INSERT INTO users(email,password_hash,role,status,student_id,teacher_id)
            VALUES(%s,%s,%s,%s,%s,%s) RETURNING user_id""",
            (
                email,
                generate_password_hash(password),
                role,
                state,
                who if role == "student" else None,
                who if role == "teacher" else None,
            ),
        ).fetchone()[0]
        if signin:
            client.post("/auth/login", data=dict(email=email, password=password))
        return uid

    return create
