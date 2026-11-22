# CourseLink

A local PostgreSQL-first university registration portal for CSE 3210, Database System Laboratory. Students register and view results, teachers grade assigned rosters, and administrators manage the academic catalog and approve account claims. The dataset contains fictional people and academic policies.

## Open the prepared Windows demo

In the original delivery folder, double-click **Open CourseLink.cmd** beside the project archive. Its console displays this machine’s generated accounts and starts or reconnects to the local application. Keep the console open during the demonstration. The portable source archive supports a separate installation using the instructions below.

## Install from source on Windows

Tested with Python 3.14, PostgreSQL 18.7, Flask 3.1.3 and Psycopg 3.3.9. Install Python and PostgreSQL with their command-line tools, then open PowerShell in the directory containing this README.

```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python -c "import secrets; print(secrets.token_hex(32))"
```

Set SECRET_KEY in .env to the generated string. Using psql as your local PostgreSQL installation owner, create the empty database and a restricted web login. The password command prompts privately.

```sql
CREATE DATABASE courselink;
CREATE ROLE courselink_web LOGIN;
\password courselink_web
```

Exit psql with `\q`. From the project directory run the following with your installation owner's name in place of postgres if needed. For pgAdmin, connect Query Tool to the new database and run the same two SQL files in order.

```powershell
psql -U postgres -d courselink -v ON_ERROR_STOP=1 -f database/courselink.sql
psql -U postgres -d courselink -v ON_ERROR_STOP=1 -f database/permissions.sql
```

In .env, set DATABASE_URL to the connection URI for courselink_web. Percent-encode reserved characters in URI passwords. Keep debug disabled. Set COOKIE_SECURE=1 only when serving over HTTPS.

### Provision accounts

Set OWNER_DATABASE_URL temporarily in a private PowerShell session. Use a PostgreSQL URI for the database owner that points to **courselink**. To avoid putting the password into command history, read the URI at the prompt.

```powershell
$ownerUri = Read-Host 'Owner PostgreSQL URI' -AsSecureString
$env:OWNER_DATABASE_URL = [Net.NetworkCredential]::new('', $ownerUri).Password
```

For the full classroom demonstration on a fresh database, run the fixture provisioner once. It prints generated passwords once, after committing all six accounts. Keep them in a private password manager.

```powershell
.\.venv\Scripts\python scripts/demo_accounts.py
```

For a fresh installation with just an administrator, use the interactive bootstrap instead.

```powershell
.\.venv\Scripts\python -m flask --app app bootstrap-admin
```

Remove the owner URI from the shell before starting the server.

```powershell
Remove-Item Env:OWNER_DATABASE_URL
.\.venv\Scripts\python run.py
```

Open [the local portal](http://127.0.0.1:5000). Browser assets, including Bootstrap 5.3.3, are served locally. Demo accounts use the domain courselink.example. The office account administers the portal, riya is student 1, mira teaches offering 13, and sami grades offering 10.

## Project map

| Location | Purpose |
|---|---|
| app/ | Application factory, authentication, authorization, database access and role blueprints |
| app/templates/ and app/static/ | Shared navigation, forms, dashboards, local CSS and campus illustration |
| database/ | Atomic schema/fixture installation and separate runtime grants |
| scripts/ | Local-only account provisioning |
| tests/ | PostgreSQL, Flask HTTP and concurrent acceptance checks |
| docs/ | [Architecture](docs/architecture.md), [schema](docs/database_design.md), [ER diagram](docs/er_diagram.md), [SQL](docs/sql_reference.md), [routes](docs/routes.md), [tests](docs/testing.md), [demo](docs/demonstration.md), [decisions](docs/decisions.md) and [limitations](docs/limitations.md) |

## Troubleshooting

- **Database unavailable** — confirm the PostgreSQL process, port, database name and web login in DATABASE_URL. Use a database owner only for installation, tests and bootstrap.
- **Permission denied on function or table** — apply permissions.sql in the application database. The login must inherit the courselink_web grants.
- **Account has no access** — an administrator reviews the linked identity before activation. A disabled account loses access on the next protected request.
- **Conflicting record change** — inspect uniqueness, capacity, offering lifecycle and existing academic history. Grade all active enrollments before completing an offering.
- **CSRF rejection** — reload the form and confirm that cookies are enabled. Secure cookies require HTTPS.
- **Existing database objects** — initialization targets an empty database. Create a separate empty database for another installation. A failed setup does not justify deleting existing academic data.

Follow the [classroom walkthrough](docs/demonstration.md) for registration, grading and concurrency scenarios. The [testing guide](docs/testing.md) explains the separate test database setup.
