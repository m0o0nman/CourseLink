# Database design

| Table | Primary key | Other columns and dependencies |
|---|---|---|
| departments | dept_id | Unique dept_code identifies name |
| students | student_id | full_name, unique academic email, batch, dept_id → departments |
| teachers | teacher_id | full_name, unique academic email, dept_id → departments |
| courses | course_id | Unique course_code, title, positive one-decimal credits, dept_id → departments |
| course_offerings | offering_id | course_id → courses, teacher_id → teachers, semester, year, section, capacity, status. Course/term/section is an alternate key |
| prerequisites | (course_id, prereq_course_id) | Both columns reference courses. The entire pair determines minimum_grade_point |
| enrollments | enrollment_id | student_id → students, offering_id → course_offerings, status, grade_point, enrolled_at. Student/offering is an alternate key |
| enrollment_audit | audit_id | enrollment_id → enrollments, action, action_time |
| users | user_id | email, password_hash, role, status, created_at, optional unique student_id/teacher_id. A unique lower(email) index supports login |

Each row describes one identity, relationship or event. Non-key facts depend on the key of their own relation. In particular, grades depend on the enrollment, capacity on the offering, and credit weight on the course. A department name occurs only in departments. Academic and login email have separate meanings. These dependencies motivate third normal form. Occupancy and GPA are derived through views.

Foreign keys restrict deletion of referenced records. Enrollment and audit deletion are unavailable to the web role. Status checks require null grades for enrolled/dropped records and valid non-null grades for completed records. A direct prerequisite self-reference fails a check constraint.

An offering progresses draft → open → closed → completed. Only open offerings accept enrollment and withdrawal. Completion requires resolution of all enrolled records. Academic history freezes the course, teacher, term and section of an offering and freezes course credits and course code. Capacity may increase or decrease down to occupancy.

An enrolled record can become dropped while registration is open or completed through grading after closure. A completed grade can be corrected. A dropped record permanently reserves its exact student/offering key. The student lock serializes same-term checks across sections.

The enrollment primary/unique indexes support exact identity and student history lookups. Additional indexes support offering status counts, term and instructor filters, department joins, reverse prerequisite lookup and audit navigation. Small fixture tables may be cheaper to scan sequentially. Consult the [SQL reference](sql_reference.md) to inspect the plan.
