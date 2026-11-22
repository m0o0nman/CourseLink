# SQL reference

Use READ COMMITTED, PostgreSQL’s installation default. Functions take part in the caller’s transaction and return a text code. Unexpected database exceptions propagate to the transaction manager. SECURITY DEFINER routines fix the search path, place pg_temp last and use no dynamic SQL. PUBLIC execution is revoked and the web login has explicit routine grants.

| Operation | Validation, locks and result |
|---|---|
| register_student(student, offering) | Locks student then offering, then shares the course row while recording credit history. Checks existence, open status, exact duplicate, same course/term record, every prerequisite and occupancy. Inserts once and returns REGISTERED. Other results are STUDENT_NOT_FOUND, OFFERING_NOT_FOUND, OFFERING_NOT_OPEN, ALREADY_REGISTERED, COURSE_ALREADY_TAKEN_THIS_TERM, PREREQUISITE_NOT_SATISFIED and OFFERING_FULL |
| withdraw_student(student, offering) | Locks student then offering. Checks existence and open status, then changes the caller's enrolled record to dropped. Returns WITHDRAWN, NO_ACTIVE_ENROLLMENT or the applicable existence/open status code |
| submit_grade(teacher, enrollment, grade) | Locks the offering and checks assignment. A closed offering permits initial grading or correction. A completed offering permits correction. Updates grade and status together. Returns GRADED, UNAUTHORIZED, NOT_GRADABLE or INVALID_GRADE |
| log_enrollment() | AFTER INSERT logs ENROLLED. AFTER UPDATE logs WITHDRAWN only on a transition to dropped. Other updates return without logging |
| protect_offering(), protect_course() | BEFORE triggers check lifecycle, occupancy and academic-history restrictions. Admin edits acquire the target row before running the update in a separate statement in the same transaction |
| offering_enrollment_summary | Left-joins enrolled/completed records so empty offerings appear. Remaining seats equal capacity minus occupied seats |
| student_gpa | Starts with all students. Completed credits weight each grade. NULLIF prevents zero division. The displayed result is rounded to two decimals, with NULL for no graded credits |

```sql
SELECT student_id, graded_credits, gpa FROM student_gpa ORDER BY student_id;
SELECT course_code, section, capacity, occupied_seats, remaining_seats
FROM offering_enrollment_summary ORDER BY remaining_seats, offering_id;
SELECT e.student_id,e.offering_id,a.action,a.action_time FROM enrollment_audit a
JOIN enrollments e USING(enrollment_id) ORDER BY a.audit_id;
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM enrollments
WHERE offering_id=3 AND status='enrolled';
```

The planner can choose a sequential scan on the small demonstration dataset. Compare estimated and actual rows, loops and buffers before drawing performance conclusions.

On the prepared PostgreSQL 18.7 database, the example plan used enrollment_occupancy with one index search and one returned row. This is one observed plan for the seed data.
