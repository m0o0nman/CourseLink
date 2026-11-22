from decimal import Decimal, InvalidOperation
from flask import Blueprint, abort, flash, redirect, render_template, request
from flask_login import current_user as user
from . import db, role_required

academic = Blueprint("academic", __name__)
SUMMARY = "offering_enrollment_summary"
HISTORY = """SELECT e.enrollment_id,e.status AS enrollment_status,e.grade_point,v.*
    FROM enrollments e JOIN offering_enrollment_summary v USING(offering_id)
    WHERE e.student_id=%s"""
MESSAGES = {
    "REGISTERED": "Registration confirmed.",
    "WITHDRAWN": "You have withdrawn from this offering.",
    "GRADED": "Grade saved.",
    "ALREADY_REGISTERED": "You already have a record for this offering.",
    "COURSE_ALREADY_TAKEN_THIS_TERM": "You already have this course in another section this term.",
    "PREREQUISITE_NOT_SATISFIED": "You have not met every prerequisite for this course.",
    "OFFERING_FULL": "All seats have been taken.",
    "OFFERING_NOT_OPEN": "Registration is closed for this offering.",
    "NO_ACTIVE_ENROLLMENT": "You have no active registration in this offering.",
    "NOT_GRADABLE": "This record is not eligible for grading.",
    "INVALID_GRADE": "Enter a grade from 0.00 to 4.00 with up to two decimal places.",
}


def feedback(result):
    if result in ("OFFERING_NOT_FOUND", "STUDENT_NOT_FOUND"):
        abort(404)
    if result == "UNAUTHORIZED":
        abort(403)
    flash(
        MESSAGES[result],
        "success" if result in ("REGISTERED", "WITHDRAWN", "GRADED") else "error",
    )


@academic.get("/student/dashboard")
@role_required("student")
def student_dashboard():
    s = user.student_id
    stats = db.first(
        """SELECT count(*) courses,coalesce(sum(credits),0) credits FROM enrollments
        JOIN offering_enrollment_summary USING(offering_id) WHERE student_id=%s AND enrollments.status='enrolled'""",
        (s,),
    )
    gpa = db.first("SELECT gpa FROM student_gpa WHERE student_id=%s", (s,))["gpa"]
    items = db.rows(
        HISTORY + " AND e.status='enrolled' ORDER BY year DESC,semester,course_code",
        (s,),
    )
    return render_template(
        "academic.html",
        title="Student overview",
        items=items,
        section="Current registrations",
        cards={
            "Enrolled courses": stats["courses"],
            "Registered credits": stats["credits"],
            "Demo weighted GPA": gpa,
        },
        action=("/student/courses", "Browse courses"),
    )


@academic.get("/student/courses")
@academic.get("/catalog")
@role_required("student", "teacher", "admin")
def catalog():
    if request.path.startswith("/student/") and user.role != "student":
        abort(403)
    term = request.args.get("semester", "")
    year = request.args.get("year", "")
    department = request.args.get("department", "")
    keyword = request.args.get("q", "").strip()
    if (
        year and (not year.isascii() or not year.isdigit() or len(year) != 4)
    ) or term not in ("", "Spring", "Summer", "Fall"):
        abort(400)
    items = db.rows(
        """SELECT * FROM offering_enrollment_summary WHERE
        (course_code ILIKE %s OR title ILIKE %s) AND (%s='' OR semester=%s)
        AND (%s='' OR year::text=%s) AND (%s='' OR dept_code=%s)
        ORDER BY year DESC,course_code,section""",
        (
            "%" + keyword + "%",
            "%" + keyword + "%",
            term,
            term,
            year,
            year,
            department,
            department,
        ),
    )
    return render_template(
        "academic.html",
        title="Course catalog",
        section="Course offerings",
        items=items,
        catalog=True,
        depts=db.rows("SELECT dept_code FROM departments ORDER BY dept_code"),
    )


@academic.get("/student/registrations")
@academic.get("/student/results")
@role_required("student")
def history():
    results = request.path.endswith("/results")
    extra = " AND e.status='completed'" if results else ""
    items = db.rows(
        HISTORY + extra + " ORDER BY year DESC,offering_id", (user.student_id,)
    )
    gpa = db.first("SELECT * FROM student_gpa WHERE student_id=%s", (user.student_id,))
    return render_template(
        "academic.html",
        title="Academic results" if results else "My registrations",
        items=items,
        section="Completed courses" if results else "Enrollment history",
        cards={"Demo weighted GPA": gpa["gpa"], "Graded credits": gpa["graded_credits"]}
        if results
        else None,
    )


@academic.post("/student/enroll/<int:offering_id>")
@academic.post("/student/drop/<int:offering_id>")
@role_required("student")
def registration(offering_id):
    enroll = request.path.startswith("/student/enroll/")
    operation = "register_student" if enroll else "withdraw_student"
    feedback(
        db.first(
            f"SELECT {operation}(%s,%s) AS result", (user.student_id, offering_id)
        )["result"]
    )
    return redirect("/student/courses" if enroll else "/student/registrations")


@academic.get("/teacher/dashboard")
@role_required("teacher")
def teacher_dashboard():
    items = db.rows(
        "SELECT * FROM offering_enrollment_summary WHERE teacher_id=%s ORDER BY year DESC,course_code",
        (user.teacher_id,),
    )
    counts = db.first(
        """SELECT count(*) FILTER (WHERE e.status='enrolled') active,
        count(*) FILTER (WHERE e.status='enrolled' AND o.status='closed') awaiting FROM enrollments e
        JOIN course_offerings o USING(offering_id) WHERE teacher_id=%s""",
        (user.teacher_id,),
    )
    return render_template(
        "academic.html",
        title="Teaching overview",
        section="Assigned offerings",
        items=items,
        cards={
            "Assigned offerings": len(items),
            "Active registrations": counts["active"],
            "Awaiting grades": counts["awaiting"],
        },
    )


@academic.get("/teacher/offering/<int:offering_id>")
@role_required("teacher", "admin")
def roster(offering_id):
    offering = db.first(
        "SELECT * FROM offering_enrollment_summary WHERE offering_id=%s", (offering_id,)
    )
    if not offering:
        abort(404)
    if user.role == "teacher" and offering["teacher_id"] != user.teacher_id:
        abort(403)
    items = db.rows(
        """SELECT e.*,s.full_name FROM enrollments e JOIN students s USING(student_id)
        WHERE offering_id=%s ORDER BY s.full_name""",
        (offering_id,),
    )
    return render_template(
        "roster.html", title="Student roster", offering=offering, items=items
    )


@academic.post("/teacher/enrollment/<int:eid>/grade")
@role_required("teacher")
def grade(eid):
    try:
        value = Decimal(request.form.get("grade", ""))
        if (
            not value.is_finite()
            or not 0 <= value <= 4
            or value != value.quantize(Decimal(".01"))
        ):
            raise ValueError()
    except (InvalidOperation, ValueError):
        abort(400)
    enrollment = db.first(
        "SELECT offering_id FROM enrollments WHERE enrollment_id=%s", (eid,)
    )
    if not enrollment:
        abort(404)
    feedback(
        db.first(
            "SELECT submit_grade(%s,%s,%s) AS result", (user.teacher_id, eid, value)
        )["result"]
    )
    return redirect("/teacher/offering/" + str(enrollment["offering_id"]))
