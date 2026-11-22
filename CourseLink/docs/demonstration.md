# Classroom walkthrough

Start with a fresh fixture database and locally generated classroom accounts. Student 1 is Riya Sen. Her programming grade is 3.50 for three credits and her mathematics grade is 4.00 for two credits. The expected starting GPA is (10.50 + 8.00) ÷ 5 = 3.70.

1. Sign in as **office**. Compare the administrative counts with SELECT count(*) on the corresponding tables. Open the [ER diagram](er_diagram.md) to identify the two junction tables.
2. In Offerings create a new draft for Circuit Theory, teacher Mira Sen, Spring 2027, section C, capacity 8. Mark it open. This exercises foreign keys, the term/section alternate key and the lifecycle trigger.
3. In Account review compare Ayan's submitted claim with the fictional student 2 identity and verify it in person. Approve it. As **ayan**, attempt Database Systems Laboratory (offering 3). The prerequisite rejection leaves occupancy and audit unchanged.
4. As **riya**, filter the catalog for Database Systems Laboratory and register in section B (offering 13). Try section A to see the same-course/term rejection. In psql run the following read-only query.
   
   ```sql
   SELECT e.enrollment_id,e.student_id,e.offering_id,e.status,a.action
   FROM enrollments e JOIN enrollment_audit a USING(enrollment_id)
   WHERE e.student_id=1 AND e.offering_id=13;
   ```
5. To demonstrate withdrawal separately, register Riya in the newly created Circuit Theory section, withdraw and inspect the paired ENROLLED/WITHDRAWN audit events. The exact section cannot be reclaimed.
6. Demonstrate the last-seat lock using the initially seeded Circuit Theory offering 6. In session A run `BEGIN;` and `SELECT register_student(7,6);`. Leave it open. In session B run `SELECT register_student(8,6);`. It waits for A. Commit A and B returns OFFERING_FULL. Verify capacity 2, occupied 2 and remaining 0 in offering_enrollment_summary. Use fresh fixture data to repeat.
7. As **office**, close offering 13. As **mira**, open its roster and give Riya 4.00. Sign in as Riya and view Academic results. The GPA is now (18.50 + 1.5 × 4) ÷ 6.5 = 3.77. Compare to `SELECT * FROM student_gpa WHERE student_id=1;`.
8. As office, mark offering 13 completed. As Mira, correct the grade and observe that the event audit has no new row. Teacher Sami separately has offering 10 already closed and ready for grading.
9. Inspect the registration function, trigger definitions and actual query plan using the [SQL reference](sql_reference.md). Explain how both student and offering row locks contribute to integrity. Close with the [policy limitations](limitations.md).

The concurrency test suite repeats the races in disposable databases, so it can be rerun without changing this classroom demonstration.
