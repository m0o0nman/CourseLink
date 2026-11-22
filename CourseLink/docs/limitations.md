# Scope and limitations

CourseLink demonstrates registration rules for a fictional academic calendar. The credit-weighted overall GPA includes all completed attempts. Institutional retake rules, degree audits and official KUET grading policies require additional specifications. Students can satisfy a prerequisite with a qualifying completed record. Longer prerequisite cycles are not automatically detected.

Account claim review is an in-person classroom demonstration. Identity federation, self-service password recovery, production monitoring, rate limiting, comprehensive auditing and external notifications are outside this implementation. Administrators review grades. Assigned teachers perform corrections. Rejected and disabled identities stay claimed.

The web application trusts the local server and its PostgreSQL credentials. A database owner can alter the schema and data. The Flask development server binds to loopback. Use a separate deployment design before operating a public service.

Excluded academic modules include attendance, payments, timetable generation, conflict detection, waitlists and graduation tracking. The portal has no mobile app, public API, cloud deployment or automated recommendations.
