from decimal import Decimal, InvalidOperation
from email_validator import validate_email, EmailNotValidError
from flask import Blueprint, abort, flash, redirect, render_template, request
from . import db, role_required

admin = Blueprint("admin", __name__, url_prefix="/admin")
# Fixed metadata is the only source of dynamic SQL identifiers.
ENTITIES = {
    "departments": ("departments", "dept_id", ["dept_code", "name"]),
    "students": ("students", "student_id", ["full_name", "email", "batch", "dept_id"]),
    "teachers": ("teachers", "teacher_id", ["full_name", "email", "dept_id"]),
    "courses": ("courses", "course_id", ["course_code", "title", "credits", "dept_id"]),
    "prerequisites": (
        "prerequisites",
        None,
        ["course_id", "prereq_course_id", "minimum_grade_point"],
    ),
    "offerings": (
        "course_offerings",
        "offering_id",
        ["course_id", "teacher_id", "semester", "year", "section", "capacity"],
    ),
}
LABELS = {
    "dept_id": "Department",
    "dept_code": "Department code",
    "prereq_course_id": "Required course",
    "course_id": "Course",
    "teacher_id": "Teacher",
    "minimum_grade_point": "Minimum grade point",
}


def values(fields):
    result = []
    for f in fields:
        v = request.form.get(f, "").strip()
        try:
            if not v or len(v) > 254:
                raise ValueError()
            if f.endswith("_id") or f in ("batch", "year", "capacity"):
                v = int(v)
                if not 1 <= v <= 2147483647:
                    raise ValueError()
            elif f in ("credits", "minimum_grade_point"):
                v = Decimal(v)
                if (
                    not v.is_finite()
                    or (
                        f == "credits"
                        and not (0 < v <= 999.9 and v == v.quantize(Decimal(".1")))
                    )
                    or (
                        f == "minimum_grade_point"
                        and not (0 <= v <= 4 and v == v.quantize(Decimal(".01")))
                    )
                ):
                    raise ValueError()
            elif f == "email":
                v = validate_email(
                    v, check_deliverability=False, test_environment=True
                ).normalized
            elif f == "semester" and v not in ("Spring", "Summer", "Fall"):
                raise ValueError()
            elif len(v) > (20 if f in ("dept_code", "course_code", "section") else 150):
                raise ValueError()
        except (ValueError, InvalidOperation, EmailNotValidError):
            abort(400)
        result.append(v)
    return result


@admin.get("/dashboard")
@role_required("admin")
def dashboard():
    stats = db.first("""SELECT (SELECT count(*) FROM students) "Students",(SELECT count(*) FROM teachers) "Teachers",
        (SELECT count(*) FROM courses) "Courses",(SELECT count(*) FROM course_offerings) "Offerings",
        (SELECT count(*) FROM enrollments WHERE status='enrolled') "Active registrations",
        (SELECT count(*) FROM users WHERE status='pending') "Pending approvals" """)
    return render_template(
        "academic.html",
        title="Administration overview",
        section="Offering occupancy",
        cards=stats,
        items=db.rows(
            "SELECT * FROM offering_enrollment_summary ORDER BY remaining_seats,course_code"
        ),
        action=("/admin/accounts", "Review accounts"),
    )


@admin.route("/<entity>", methods=["GET", "POST"])
@role_required("admin")
def manage(entity):
    if entity not in ENTITIES:
        abort(404)
    table, key, fields = ENTITIES[entity]
    if request.method == "POST":
        db.execute(
            f"INSERT INTO {table} ({','.join(fields)}) VALUES ({','.join(['%s'] * len(fields))})",
            values(fields),
        )
        flash("Record created.", "success")
        return redirect("/admin/" + entity)
    opts = {}
    for f, query in [
        ("dept_id", "SELECT dept_id id,dept_code label FROM departments"),
        (
            "course_id",
            "SELECT course_id id,course_code || ' · ' || title label FROM courses",
        ),
        ("teacher_id", "SELECT teacher_id id,full_name label FROM teachers"),
    ]:
        if f in fields:
            opts[f] = db.rows(query + " ORDER BY label")
    opts["prereq_course_id"] = opts.get("course_id", [])
    opts["semester"] = [dict(id=s, label=s) for s in ("Spring", "Summer", "Fall")]
    source = "offering_enrollment_summary" if entity == "offerings" else table
    return render_template(
        "manage.html",
        title=entity.title(),
        entity=entity,
        fields=fields,
        labels=LABELS,
        opts=opts,
        key=key,
        items=db.rows(f"SELECT * FROM {source} ORDER BY 1"),
    )


@admin.post("/<entity>/<int:record_id>/edit")
@role_required("admin")
def edit(entity, record_id):
    if entity not in ENTITIES or entity == "prerequisites":
        abort(404)
    table, key, fields = ENTITIES[entity]
    params = values(fields)
    with db.transaction() as conn:
        # Serialize occupancy-sensitive edits with the registration functions.
        if not conn.execute(
            f"SELECT 1 FROM {table} WHERE {key}=%s FOR UPDATE", (record_id,)
        ).fetchone():
            abort(404)
        assignments = ",".join(f + "=%s" for f in fields)
        conn.execute(
            f"UPDATE {table} SET {assignments} WHERE {key}=%s", (*params, record_id)
        )
    flash("Record saved.", "success")
    return redirect("/admin/" + entity)


@admin.post("/offerings/<int:oid>/status")
@role_required("admin")
def offering_status(oid):
    state = request.form.get("status")
    if state not in ("open", "closed", "completed"):
        abort(400)
    with db.transaction() as conn:
        if not conn.execute(
            "SELECT 1 FROM course_offerings WHERE offering_id=%s FOR UPDATE", (oid,)
        ).fetchone():
            abort(404)
        conn.execute(
            "UPDATE course_offerings SET status=%s WHERE offering_id=%s", (state, oid)
        )
    flash("Offering status updated.", "success")
    return redirect("/admin/offerings")


@admin.post("/prerequisites/delete")
@role_required("admin")
def delete_prerequisite():
    if not db.execute(
        "DELETE FROM prerequisites WHERE course_id=%s AND prereq_course_id=%s",
        values(["course_id", "prereq_course_id"]),
    ):
        abort(404)
    flash("Prerequisite removed.", "success")
    return redirect("/admin/prerequisites")


@admin.get("/accounts")
@role_required("admin")
def accounts():
    items = db.rows("""SELECT u.user_id,u.email,u.role,u.status,coalesce(s.full_name,t.full_name,'Administrator') name,
        coalesce(s.student_id,t.teacher_id) academic_id, coalesce(s.email,t.email) contact FROM users u
        LEFT JOIN students s USING(student_id) LEFT JOIN teachers t USING(teacher_id)
        ORDER BY (u.status='pending') DESC,u.user_id""")
    return render_template("accounts.html", title="Account review", items=items)


@admin.post("/accounts/<int:uid>/<action>")
@role_required("admin")
def account_action(uid, action):
    states = {
        "approve": ("pending", "active"),
        "reject": ("pending", "rejected"),
        "disable": ("active", "disabled"),
    }
    if action not in states:
        abort(404)
    old, new = states[action]
    if not db.execute(
        "UPDATE users SET status=%s WHERE user_id=%s AND status=%s AND role<>'admin'",
        (new, uid, old),
    ):
        abort(409)
    flash("Account status updated.", "success")
    return redirect("/admin/accounts")


@admin.get("/audit")
@role_required("admin")
def audit():
    items = db.rows("""SELECT a.audit_id,a.action_time,s.full_name,v.course_code,v.section,v.semester,v.year,
        a.enrollment_id,a.action FROM enrollment_audit a JOIN enrollments e USING(enrollment_id)
        JOIN students s USING(student_id) JOIN offering_enrollment_summary v USING(offering_id) ORDER BY a.audit_id DESC""")
    return render_template("audit.html", title="Enrollment audit", items=items)


@admin.get("/records")
@role_required("admin")
def records():
    items = db.rows("""SELECT s.full_name,g.student_id,g.graded_credits,g.gpa FROM student_gpa g
        JOIN students s USING(student_id) ORDER BY s.full_name""")
    return render_template("records.html", title="Academic records", items=items)
