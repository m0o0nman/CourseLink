import os
from functools import wraps
import click
import psycopg
from dotenv import load_dotenv
from flask import Flask, abort, redirect, render_template, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required
from flask_wtf.csrf import CSRFProtect
from werkzeug.exceptions import Conflict, BadRequest
from werkzeug.security import generate_password_hash
from email_validator import validate_email, EmailNotValidError
from . import db

login = LoginManager()
login.login_view = "auth.login_page"


class User(UserMixin):
    def __init__(self, record):
        self.__dict__.update(record)
        self.id = str(self.user_id)


@login.user_loader
def load_user(user_id):
    record = db.first(
        """SELECT u.user_id,u.email,u.role,u.student_id,u.teacher_id,
        coalesce(s.full_name,t.full_name,'Administrator') AS name FROM users u
        LEFT JOIN students s USING(student_id) LEFT JOIN teachers t USING(teacher_id)
        WHERE u.user_id=%s AND u.status='active'""",
        (user_id,),
    )
    return User(record) if record else None


def role_required(*roles):
    def decorate(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorate


def create_app(config=None):
    load_dotenv()
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY"),
        DATABASE_URL=os.getenv("DATABASE_URL"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE") == "1",
        MAX_CONTENT_LENGTH=65536,
    )
    app.config.update(config or {})
    if not app.config["SECRET_KEY"] or not app.config["DATABASE_URL"]:
        raise RuntimeError("Configure SECRET_KEY and DATABASE_URL in .env first.")
    login.init_app(app)
    CSRFProtect(app)
    from .auth import auth
    from .academic import academic
    from .admin import admin

    for blueprint in (auth, academic, admin):
        app.register_blueprint(blueprint)

    @app.get("/")
    def home():
        if current_user.is_authenticated:
            return redirect("/" + current_user.role + "/dashboard")
        return redirect(url_for("auth.login_page"))

    @app.after_request
    def headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    def problem(error):
        code = getattr(error, "code", 500)
        reason = {
            400: "Check the submitted fields or reload the form.",
            403: "Your account cannot access this record.",
            404: "This record or page could not be found.",
            409: "The change conflicts with existing academic records.",
            500: "The request could not be completed.",
            503: "The academic database is unavailable.",
        }
        return render_template(
            "error.html",
            title="Request unavailable",
            message=reason.get(code, "Request failed."),
            code=code,
        ), code

    for code in (400, 403, 404, 409, 500, 503):
        app.register_error_handler(code, problem)

    @app.errorhandler(psycopg.IntegrityError)
    def integrity(error):
        return problem(Conflict())

    @app.errorhandler(psycopg.DataError)
    def invalid_value(error):
        return problem(BadRequest())

    @app.errorhandler(psycopg.OperationalError)
    def unavailable(error):
        # Standalone page avoids querying the account loader during an outage.
        return (
            "CourseLink is unable to connect to PostgreSQL. Check the database service.",
            503,
        )

    @app.cli.command("bootstrap-admin")
    @click.option("--email", prompt=True)
    @click.password_option()
    def bootstrap(email, password):
        """Create the first administrator with the database owner's connection."""
        if len(password) < 12:
            raise click.ClickException("Use at least 12 characters.")
        try:
            email = validate_email(email, check_deliverability=False).normalized.lower()
        except EmailNotValidError as error:
            raise click.ClickException(str(error)) from error
        with psycopg.connect(os.environ["OWNER_DATABASE_URL"]) as conn:
            conn.execute("LOCK TABLE users IN SHARE ROW EXCLUSIVE MODE")
            if conn.execute("SELECT 1 FROM users WHERE role='admin'").fetchone():
                raise click.ClickException("An administrator already exists.")
            conn.execute(
                "INSERT INTO users(email,password_hash,role,status) VALUES(%s,%s,'admin','active')",
                (email, generate_password_hash(password)),
            )
        click.echo("Administrator created.")

    return app
