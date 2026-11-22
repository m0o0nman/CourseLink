"""Short, independent READ COMMITTED transactions. Multi-step writes use transaction()."""

from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row
from flask import current_app


@contextmanager
def transaction():
    with psycopg.connect(
        current_app.config["DATABASE_URL"], row_factory=dict_row
    ) as conn:
        yield conn


def rows(query, params=()):
    with transaction() as conn:
        return conn.execute(query, params).fetchall()


def first(query, params=()):
    result = rows(query, params)
    return result[0] if result else None


def execute(query, params=()):
    with transaction() as conn:
        return conn.execute(query, params).rowcount
