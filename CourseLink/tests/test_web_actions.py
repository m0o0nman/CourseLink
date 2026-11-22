import pytest


@pytest.mark.parametrize(
    "entity,data,field,updated",
    [
        (
            "departments",
            dict(dept_code="ARC", name="Architecture"),
            "name",
            "Architectural Design",
        ),
        (
            "students",
            dict(
                full_name="Test Student", email="one@example.org", batch=2026, dept_id=1
            ),
            "batch",
            2027,
        ),
        (
            "teachers",
            dict(full_name="Test Teacher", email="two@example.org", dept_id=2),
            "dept_id",
            3,
        ),
        (
            "courses",
            dict(course_code="LAB 100", title="Lab Practice", credits="1.5", dept_id=1),
            "credits",
            "2.0",
        ),
    ],
)
def test_admin_directory_actions(client, conn, identity, entity, data, field, updated):
    from app.admin import ENTITIES

    identity("admin")
    assert client.post("/admin/" + entity, data=data).status_code == 302
    table, key, _ = ENTITIES[entity]
    record = conn.execute(f"SELECT max({key}) FROM {table}").fetchone()[0]
    assert (
        client.post(
            f"/admin/{entity}/{record}/edit", data=data | {field: updated}
        ).status_code
        == 302
    )
    value = conn.execute(
        f"SELECT {field} FROM {table} WHERE {key}=%s", (record,)
    ).fetchone()[0]
    assert str(value) == str(updated)


def test_account_and_prerequisite_actions(client, conn, identity):
    identity("admin")
    pair = {"course_id": 10, "prereq_course_id": 2}
    assert (
        client.post(
            "/admin/prerequisites", data=pair | {"minimum_grade_point": "2.75"}
        ).status_code
        == 302
    )
    assert client.post("/admin/prerequisites/delete", data=pair).status_code == 302
    assert (
        conn.execute(
            "SELECT 1 FROM prerequisites WHERE course_id=10 AND prereq_course_id=2"
        ).fetchone()
        is None
    )
    for state, action, expected in [
        ("active", "disable", "disabled"),
        ("pending", "reject", "rejected"),
    ]:
        uid = identity("student", 1 if state == "active" else 2, state, False)
        assert client.post(f"/admin/accounts/{uid}/{action}").status_code == 302
        assert (
            conn.execute(
                "SELECT status FROM users WHERE user_id=%s", (uid,)
            ).fetchone()[0]
            == expected
        )


def test_grade_correction_after_completion(conn):
    assert (
        conn.execute(
            "SELECT submit_grade(4,enrollment_id,4) FROM enrollments WHERE offering_id=10"
        ).fetchone()[0]
        == "GRADED"
    )
    conn.execute("UPDATE course_offerings SET status='completed' WHERE offering_id=10")
    assert (
        conn.execute(
            "SELECT submit_grade(4,enrollment_id,3.75) FROM enrollments WHERE offering_id=10"
        ).fetchone()[0]
        == "GRADED"
    )
