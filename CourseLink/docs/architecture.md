# Architecture

The browser submits HTML forms to Flask blueprints. Jinja escapes field values. Flask-WTF validates CSRF tokens globally, including forms implemented directly in HTML. Flask-Login stores a user identifier in a signed session cookie. Every protected request reloads the identity from PostgreSQL with status='active'. The role decorator runs before resource-specific authorization.

The academic blueprint derives the student or teacher identity from that account. Registration and withdrawal pass the authenticated student ID to SQL. Roster reads check the assigned teacher before rendering. Grade writes check the assignment under an offering lock inside submit_grade. Administrators can inspect rosters and results.

The database access layer opens a connection per operation and uses Psycopg connection contexts to commit or roll back. Multi-statement admin edits share one transaction. Psycopg binds all submitted values as parameters. Interpolated table and column identifiers come from server-owned metadata.

The web role can read academic data and manage catalog records. Enrollment mutations require approved SECURITY DEFINER functions. The owner is trusted and used only during setup. Access control for individual browser users resides in Flask. The database login identifies the application, so possession of its credential permits invoking allowed routines with arbitrary IDs. Keep that credential local and private.

The enrollment audit trigger runs in the caller’s transaction. No queue or background processor is involved. A rejected registration returns a reason before insertion. A failed transaction rolls back its enrollment and audit events together.
