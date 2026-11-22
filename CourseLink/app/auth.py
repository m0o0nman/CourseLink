from flask import Blueprint, flash, redirect, render_template, session
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, IntegerField
from wtforms.validators import InputRequired, Length, EqualTo, Email, NumberRange
from werkzeug.security import check_password_hash, generate_password_hash
import psycopg
from . import db, load_user

auth = Blueprint("auth", __name__)


class LoginForm(FlaskForm):
    email = StringField(
        "Login email",
        validators=[
            InputRequired(),
            Email(check_deliverability=False),
            Length(max=254),
        ],
    )
    password = PasswordField("Password", validators=[InputRequired(), Length(max=256)])


class ClaimForm(LoginForm):
    role = SelectField(
        "Account type", choices=[("student", "Student"), ("teacher", "Teacher")]
    )
    academic_id = IntegerField(
        "Academic ID", validators=[InputRequired(), NumberRange(1, 2147483647)]
    )
    password = PasswordField("Password", validators=[Length(min=12, max=256)])
    confirm = PasswordField(
        "Confirm password", validators=[InputRequired(), EqualTo("password")]
    )


@auth.route("/auth/login", methods=["GET", "POST"])
def login_page():
    if current_user.is_authenticated:
        return redirect("/")
    form = LoginForm()
    if form.validate_on_submit():
        user = db.first(
            "SELECT user_id,password_hash,status FROM users WHERE lower(email)=%s",
            (form.email.data.strip().lower(),),
        )
        if user and check_password_hash(user["password_hash"], form.password.data):
            if user["status"] == "active":
                session.clear()
                account = load_user(user["user_id"])
                if account:
                    login_user(account)
                    return redirect("/")
            flash("This account does not currently have portal access.", "error")
        else:
            flash("Check your login email and password.", "error")
    return render_template("auth.html", form=form, signup=False, title="Welcome back")


@auth.route("/auth/register", methods=["GET", "POST"])
def register():
    form = ClaimForm()
    if form.validate_on_submit():
        role = form.role.data
        try:
            db.execute(
                """INSERT INTO users(email,password_hash,role,student_id,teacher_id)
                VALUES(%s,%s,%s,%s,%s)""",
                (
                    form.email.data.strip().lower(),
                    generate_password_hash(form.password.data),
                    role,
                    form.academic_id.data if role == "student" else None,
                    form.academic_id.data if role == "teacher" else None,
                ),
            )
        except psycopg.IntegrityError:
            flash("Unable to submit this claim. Contact the academic office.", "error")
        else:
            flash(
                "Account request received. An administrator will review your academic identity.",
                "success",
            )
            return redirect("/auth/login")
    return render_template(
        "auth.html", form=form, signup=True, title="Request an account"
    )


@auth.post("/auth/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect("/auth/login")


@auth.get("/account/profile")
@login_required
def profile():
    user = current_user
    profile = {"Name": user.name, "Login email": user.email, "Role": user.role}
    if user.role in ("student", "teacher"):
        table, key = (
            ("students", "student_id")
            if user.role == "student"
            else ("teachers", "teacher_id")
        )
        data = db.first(
            f"SELECT a.*,d.name AS department FROM {table} a JOIN departments d USING(dept_id) WHERE {key}=%s",
            (getattr(user, key),),
        )
        profile.update(
            {
                "Academic ID": data[key],
                "Contact email": data["email"],
                "Department": data["department"],
            }
        )
        if "batch" in data:
            profile["Batch"] = data["batch"]
    return render_template("profile.html", title="My profile", profile=profile)
