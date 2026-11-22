import secrets
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
import psycopg
import pytest


def scalar(c, query, args=()):
    return c.execute(query, args).fetchone()[0]


def register(c, student=1, offering=3):
    return scalar(c, "SELECT register_student(%s,%s)", (student, offering))


def grade(c, teacher=4, value=3):
    return scalar(
        c,
        "SELECT submit_grade(%s,enrollment_id,%s) FROM enrollments WHERE offering_id=10",
        (teacher, value),
    )


def claim():
    password = secrets.token_urlsafe(16)
    return dict(
        role="student",
        academic_id=17,
        email="new@example.org",
        password=password,
        confirm=password,
    )


def test_T01_initialize(conn):
    assert (
        scalar(
            conn,
            "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'",
        )
        == 9
    )


def test_T02_student(conn):
    assert (
        scalar(
            conn,
            "INSERT INTO students(full_name,batch,email,dept_id) VALUES('Test',2025,'t@example.org',1) RETURNING student_id",
        )
        > 20
    )


def test_T03_foreign_key(conn):
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conn.execute(
            "INSERT INTO teachers(full_name,email,dept_id) VALUES('Test','t@example.org',999)"
        )


def test_T04_pending_claim(client, conn):
    client.post("/auth/register", data=claim())
    assert scalar(conn, "SELECT status FROM users WHERE student_id=17") == "pending"


def test_T05_duplicate_claim(client, conn):
    data = claim()
    client.post("/auth/register", data=data)
    data["email"] = "other@example.org"
    assert b"Unable to submit" in client.post("/auth/register", data=data).data
    assert scalar(conn, "SELECT count(*) FROM users") == 1


def test_T06_incorrect_password(client, identity, conn):
    identity(signin=False)
    response = client.post(
        "/auth/login",
        data=dict(email=scalar(conn, "SELECT email FROM users"), password="wrong"),
    )
    assert (
        b"Check your login" in response.data
        and client.get("/student/dashboard").status_code == 302
    )


@pytest.mark.parametrize("state", ["pending", "disabled", "rejected"])
def test_T07_inactive(client, identity, state):
    identity(state=state)
    assert "/auth/login" in client.get("/student/dashboard").location


def test_T08_approval(client, identity, conn):
    identity("admin")
    uid = identity("teacher", state="pending", signin=False)
    client.post(f"/admin/accounts/{uid}/approve")
    assert scalar(conn, "SELECT status FROM users WHERE user_id=%s", (uid,)) == "active"


def test_T09_role(client, identity):
    identity()
    assert client.get("/admin/dashboard").status_code == 403


def test_T10_teacher_ownership(client, identity, conn):
    identity("teacher", 1)
    assert client.get("/teacher/offering/10").status_code == 403
    eid = scalar(conn, "SELECT enrollment_id FROM enrollments WHERE offering_id=10")
    assert (
        client.post(f"/teacher/enrollment/{eid}/grade", data={"grade": 4}).status_code
        == 403
    )


def test_T11_enroll(conn):
    assert register(conn) == "REGISTERED"


def test_T12_duplicate(conn):
    assert register(conn, 4) == "ALREADY_REGISTERED"


def test_T13_section(conn):
    assert register(conn, 4, 13) == "COURSE_ALREADY_TAKEN_THIS_TERM"


@pytest.mark.parametrize("student", [2, 3])
def test_T14_prerequisite(conn, student):
    assert register(conn, student) == "PREREQUISITE_NOT_SATISFIED"


def test_T15_full(conn):
    assert register(conn, 2, 5) == "OFFERING_FULL"


def race(url, operations):
    gate = Barrier(len(operations))

    def run(op):
        with psycopg.connect(url) as c:
            gate.wait(timeout=15)
            return op(c)

    with ThreadPoolExecutor(len(operations)) as pool:
        return list(pool.map(run, operations))


def test_T16_last_seat(conn, urls):
    results = race(urls[1], [lambda c: register(c, 1, 6), lambda c: register(c, 2, 6)])
    assert sorted(results) == ["OFFERING_FULL", "REGISTERED"]
    assert (
        scalar(
            conn,
            "SELECT remaining_seats FROM offering_enrollment_summary WHERE offering_id=6",
        )
        == 0
    )


def test_T17_withdraw(conn):
    assert scalar(conn, "SELECT withdraw_student(4,3)") == "WITHDRAWN"
    assert (
        scalar(conn, "SELECT count(*) FROM enrollment_audit WHERE action='WITHDRAWN'")
        == 1
    )
    assert (
        register(conn, 4, 3) == "ALREADY_REGISTERED"
        and register(conn, 4, 13) == "REGISTERED"
    )


def test_T18_invalid_withdraw(conn):
    assert scalar(conn, "SELECT withdraw_student(4,10)") == "OFFERING_NOT_OPEN"
    assert scalar(conn, "SELECT withdraw_student(2,3)") == "NO_ACTIVE_ENROLLMENT"


def test_T19_grade_gpa(conn):
    assert grade(conn) == "GRADED"
    assert scalar(conn, "SELECT gpa FROM student_gpa WHERE student_id=1") == Decimal(
        "3.44"
    )


def test_T20_grade_range(conn):
    assert grade(conn, value=Decimal("4.1")) == "INVALID_GRADE"


def test_T21_rollback(conn):
    with pytest.raises(RuntimeError), conn.transaction():
        conn.execute("UPDATE departments SET name='Changed' WHERE dept_id=1")
        raise RuntimeError()
    assert (
        scalar(conn, "SELECT name FROM departments WHERE dept_id=1")
        == "Computer Science and Engineering"
    )


def test_T22_weighted_average(conn):
    assert (
        scalar(conn, "SELECT gpa FROM student_gpa WHERE student_id=1")
        == (Decimal("3.5") * 3 + 4 * 2) / 5
    )


def test_T23_events(conn):
    before = scalar(conn, "SELECT count(*) FROM enrollment_audit")
    grade(conn)
    grade(conn, value=4)
    assert scalar(conn, "SELECT count(*) FROM enrollment_audit") == before
    assert scalar(conn, "SELECT withdraw_student(4,3)") == "WITHDRAWN"
    assert {
        r[0] for r in conn.execute("SELECT DISTINCT action FROM enrollment_audit")
    } == {"ENROLLED", "WITHDRAWN"}


def test_T24_dashboard(client, identity, conn):
    identity()
    page = client.get("/student/dashboard").data
    assert (
        str(scalar(conn, "SELECT gpa FROM student_gpa WHERE student_id=1")).encode()
        in page
    )
    assert b"Computer Networks" in page


def test_T25_completed_occupancy(conn):
    before = scalar(
        conn,
        "SELECT occupied_seats FROM offering_enrollment_summary WHERE offering_id=10",
    )
    grade(conn)
    assert (
        scalar(
            conn,
            "SELECT occupied_seats FROM offering_enrollment_summary WHERE offering_id=10",
        )
        == before
        == 1
    )


def test_T26_capacity(conn):
    register(conn, 1, 6)
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("UPDATE course_offerings SET capacity=1 WHERE offering_id=6")


def test_T27_revocation(client, identity, conn):
    uid = identity()
    assert client.get("/student/dashboard").status_code == 200
    conn.execute("UPDATE users SET status='disabled' WHERE user_id=%s", (uid,))
    assert client.get("/student/dashboard").status_code == 302


def test_T28_public_admin(client, conn):
    client.post("/auth/register", data=claim() | {"role": "admin"})
    assert scalar(conn, "SELECT count(*) FROM users") == 0


def test_T29_student_ownership(client, identity, conn):
    identity()
    client.post("/student/drop/3", data={"student_id": 4})
    assert (
        scalar(
            conn, "SELECT status FROM enrollments WHERE student_id=4 AND offering_id=3"
        )
        == "enrolled"
    )
    assert (
        b"Database Systems Laboratory" not in client.get("/student/registrations").data
    )


@pytest.mark.parametrize(
    "query",
    [
        "INSERT INTO enrollments(student_id,offering_id) VALUES(1,3)",
        "DELETE FROM enrollments",
        "UPDATE enrollments SET status='dropped'",
        "DELETE FROM enrollment_audit",
    ],
)
def test_T30_restricted(urls, query):
    with (
        psycopg.connect(urls[1]) as c,
        pytest.raises(psycopg.errors.InsufficientPrivilege),
    ):
        c.execute(query)


def test_T31_audit_rollback(conn):
    before = scalar(conn, "SELECT count(*) FROM enrollment_audit")
    with pytest.raises(RuntimeError), conn.transaction():
        assert register(conn) == "REGISTERED"
        raise RuntimeError()
    assert scalar(conn, "SELECT count(*) FROM enrollment_audit") == before
    assert register(conn) == "REGISTERED"


def test_T32_simultaneous_sections(conn, urls):
    assert sorted(
        race(urls[1], [lambda c: register(c, 1, 3), lambda c: register(c, 1, 13)])
    ) == ["COURSE_ALREADY_TAKEN_THIS_TERM", "REGISTERED"]
    assert (
        scalar(
            conn,
            "SELECT count(*) FROM enrollments WHERE student_id=1 AND offering_id IN (3,13)",
        )
        == 1
    )


def test_T33_concurrent_claim(conn, urls):
    def create(c):
        try:
            c.execute(
                "INSERT INTO users(email,password_hash,role,student_id) VALUES(%s,'fixture','student',1)",
                (secrets.token_hex(4) + "@example.org",),
            )
            return True
        except psycopg.errors.UniqueViolation:
            return False

    assert sorted(race(urls[1], [create, create])) == [False, True]
    assert scalar(conn, "SELECT count(*) FROM users WHERE student_id=1") == 1


def test_T34_correction(conn):
    assert grade(conn) == "GRADED"
    assert grade(conn, teacher=1, value=1) == "UNAUTHORIZED"
    assert scalar(conn, "SELECT grade_point FROM enrollments WHERE offering_id=10") == 3


def test_T35_csrf(client):
    client.application.config["WTF_CSRF_ENABLED"] = True
    for token in ("", "wrong"):
        assert (
            client.post("/auth/logout", data={"csrf_token": token}).status_code == 400
        )


def test_T36_transition(conn):
    assert scalar(conn, "SELECT withdraw_student(4,3)") == "WITHDRAWN"
    assert scalar(conn, "SELECT withdraw_student(4,3)") == "NO_ACTIVE_ENROLLMENT"
    assert (
        scalar(
            conn,
            "SELECT submit_grade(3,enrollment_id,3) FROM enrollments WHERE offering_id=3",
        )
        == "NOT_GRADABLE"
    )


@pytest.mark.parametrize(
    "query",
    [
        "UPDATE course_offerings SET year=2028 WHERE offering_id=3",
        "UPDATE courses SET credits=4 WHERE course_id=1",
        "UPDATE course_offerings SET status='completed' WHERE offering_id=10",
    ],
)
def test_T37_history(conn, query):
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(query)


def test_T38_no_grades(conn):
    assert scalar(conn, "SELECT gpa FROM student_gpa WHERE student_id=20") is None


def test_T39_withdrawal_race(conn, urls):
    outcome = race(
        urls[1],
        [
            lambda c: scalar(c, "SELECT withdraw_student(5,5)"),
            lambda c: register(c, 2, 5),
        ],
    )
    assert outcome[0] == "WITHDRAWN" and outcome[1] in ("REGISTERED", "OFFERING_FULL")
    assert scalar(
        conn,
        "SELECT occupied_seats FROM offering_enrollment_summary WHERE offering_id=5",
    ) == int(outcome[1] == "REGISTERED")


def test_T40_portal_workflow(client, identity, conn):
    identity("admin")
    for section in (
        "dashboard",
        "departments",
        "students",
        "teachers",
        "courses",
        "prerequisites",
        "offerings",
        "audit",
        "accounts",
        "records",
    ):
        assert client.get("/admin/" + section).status_code == 200
    data = dict(
        course_id=6, teacher_id=1, semester="Spring", year=2027, section="C", capacity=8
    )
    assert client.post("/admin/offerings", data=data).status_code == 302
    oid = scalar(conn, "SELECT max(offering_id) FROM course_offerings")
    assert (
        client.post(
            f"/admin/offerings/{oid}/edit", data=data | {"capacity": 9}
        ).status_code
        == 302
    )
    assert (
        client.post(
            f"/admin/offerings/{oid}/status", data={"status": "open"}
        ).status_code
        == 302
    )
    client.post("/auth/logout")
    identity()
    for path in (
        "/student/courses?q=Circuit&year=2027",
        "/student/registrations",
        "/student/results",
        "/account/profile",
    ):
        assert client.get(path).status_code == 200
    assert (
        b"Registration confirmed"
        in client.post(f"/student/enroll/{oid}", follow_redirects=True).data
    )
    conn.execute(
        "UPDATE course_offerings SET status='closed' WHERE offering_id=%s", (oid,)
    )
    client.post("/auth/logout")
    identity("teacher")
    assert client.get("/teacher/dashboard").status_code == 200
    assert b"Riya Sen" in client.get(f"/teacher/offering/{oid}").data
    eid = scalar(
        conn, "SELECT enrollment_id FROM enrollments WHERE offering_id=%s", (oid,)
    )
    assert (
        b"Grade saved"
        in client.post(
            f"/teacher/enrollment/{eid}/grade",
            data={"grade": "3.25"},
            follow_redirects=True,
        ).data
    )
    assert scalar(
        conn, "SELECT grade_point FROM enrollments WHERE enrollment_id=%s", (eid,)
    ) == Decimal("3.25")
