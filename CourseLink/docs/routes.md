# Route contracts

Successful GETs render HTML. Successful POSTs redirect to the relevant list or role home and set a feedback message. Every modifying request requires a valid CSRF token. Missing authentication redirects to login, a wrong role or ownership returns 403, and a malformed form returns validation feedback or 400. Missing resources return 404 where individually addressed. Conflicting management edits return 409.

| Method and path | Role | Input, database operation and outcome |
|---|---|---|
| GET / | All | Redirect to login or the active role dashboard |
| GET, POST /auth/register | Public | role, academic_id, email, password, confirm. Insert pending claim with hash. Invalid fields, duplicates or missing academic references produce form feedback |
| GET, POST /auth/login | Public | email, password. Verify hash and active state, establish session, redirect to dashboard. Invalid credentials or state keep the login page |
| POST /auth/logout | Signed in | Clear session, redirect to login |
| GET /account/profile | Signed in | Read the linked academic record and own login email |
| GET /student/dashboard | Student | Own active enrollments, credits and GPA |
| GET /student/courses, GET /catalog | Student on first path, all active roles on second | Optional q, department, semester and year. Filter offering summary |
| GET /student/registrations | Student | Read own enrollment history including dropped rows |
| GET /student/results | Student | Own completed records and GPA view |
| POST /student/enroll/{offering_id} | Student | register_student with current student ID. Redirect to catalog with success or reason |
| POST /student/drop/{offering_id} | Student | withdraw_student with current student ID. Redirect to history with result |
| GET /teacher/dashboard | Teacher | Assigned offerings and count of active and ungraded registrations |
| GET /teacher/offering/{id} | Assigned teacher or admin | Check offering and read its roster |
| POST /teacher/enrollment/{id}/grade | Assigned teacher | grade. Check range/precision, invoke submit_grade and redirect to roster |
| GET /admin/dashboard | Admin | Six SQL counts and offering occupancy |
| GET, POST /admin/departments | Admin | Read directory or create using dept_code, name |
| GET, POST /admin/students | Admin | Read directory or create using full_name, email, batch, dept_id |
| GET, POST /admin/teachers | Admin | Read directory or create using full_name, email, dept_id |
| GET, POST /admin/courses | Admin | Read directory or create using course_code, title, credits, dept_id |
| GET, POST /admin/offerings | Admin | Read summary or create draft using course_id, teacher_id, semester, year, section, capacity |
| POST /admin/{entity}/{id}/edit | Admin | Update a department, student, teacher, course or offering with its creation fields. Lock existing row, then update. Offering history/capacity checks run in SQL |
| POST /admin/offerings/{id}/status | Admin | status. Lock offering, validate lifecycle and unresolved grades, update |
| GET, POST /admin/prerequisites | Admin | Read relationships or create using course_id, prereq_course_id, minimum_grade_point |
| POST /admin/prerequisites/delete | Admin | Remove the specified course/prerequisite pair |
| GET /admin/accounts | Admin | Read accounts with academic names and contact email for review |
| POST /admin/accounts/{id}/approve | Admin | Conditional pending → active update |
| POST /admin/accounts/{id}/reject | Admin | Conditional pending → rejected update |
| POST /admin/accounts/{id}/disable | Admin | Conditional active → disabled update. Admin identities are protected. Missing/ineligible account returns 409 |
| GET /admin/audit | Admin | Read chronological enrollment events with student and offering details |
| GET /admin/records | Admin | Read all students' graded credits and demo GPA |
