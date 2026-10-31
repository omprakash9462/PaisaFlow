import sqlite3
import math
import os
import uuid
import requests
import time

from dotenv import load_dotenv
from google import genai

from datetime import date
from urllib.parse import urlparse

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename


# =========================================================
# GEMINI CONFIGURATION
# =========================================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = (
    genai.Client(api_key=GEMINI_API_KEY)
    if GEMINI_API_KEY else None
)


# =========================================================
# APPLICATION CONFIGURATION
# =========================================================

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")
DATABASE = "paisaflow.db"

# Profile Image Configuration

UPLOAD_FOLDER = os.path.join(
    app.root_path,
    "static",
    "profile_photos"
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp"
}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA foreign_keys = ON")

    return conn


# =========================================================
# PROFILE IMAGE VALIDATION
# =========================================================

def allowed_image(file):

    if not file or not file.filename:
        return False

    filename = secure_filename(file.filename)

    if "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        return False

    header = file.stream.read(12)

    file.stream.seek(0)

    is_jpeg = header.startswith(b"\xff\xd8\xff")

    is_png = header.startswith(b"\x89PNG\r\n\x1a\n")

    is_webp = (
        len(header) >= 12
        and header[:4] == b"RIFF"
        and header[8:12] == b"WEBP"
    )

    return (
        (extension in {"jpg", "jpeg"} and is_jpeg)
        or (extension == "png" and is_png)
        or (extension == "webp" and is_webp)
    )


# =========================================================
# SAFE REDIRECT VALIDATION
# =========================================================

def is_safe_redirect(target):

    if not target:
        return False

    parsed_url = urlparse(target)

    return (
        not parsed_url.scheme
        and not parsed_url.netloc
        and target.startswith("/")
        and not target.startswith("//")
        and "\\" not in target
    )


def redirect_after_login(default_endpoint="dashboard"):

    next_page = request.args.get("next", "").strip()

    if is_safe_redirect(next_page):
        return redirect(next_page)

    return redirect(url_for(default_endpoint))


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_db():

    conn = get_db()

    try:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT NOT NULL,

                age INTEGER,

                gender TEXT,

                occupation TEXT,

                email TEXT UNIQUE NOT NULL,

                phone TEXT,

                password TEXT NOT NULL

            )
        """)

        # Profile Photo Migration

        columns = [
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(users)"
            ).fetchall()
        ]

        if "profile_photo" not in columns:

            conn.execute("""
                ALTER TABLE users
                ADD COLUMN profile_photo TEXT
            """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS finances (

                user_id INTEGER PRIMARY KEY,

                monthly_income REAL NOT NULL DEFAULT 0,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE

            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL,

                title TEXT NOT NULL,

                amount REAL NOT NULL,

                category TEXT NOT NULL,

                expense_date TEXT NOT NULL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE

            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_budgets (

                user_id INTEGER NOT NULL,

                budget_date TEXT NOT NULL,

                amount REAL NOT NULL DEFAULT 0,

                PRIMARY KEY (user_id, budget_date),

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE

            )
        """)
        # SAVINGS GOALS TABLE

        conn.execute("""
            CREATE TABLE IF NOT EXISTS savings_goals (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL,

                title TEXT NOT NULL,

                target_amount REAL NOT NULL,

                saved_amount REAL NOT NULL DEFAULT 0,

                target_date TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE

            )
        """)
        conn.commit()

    finally:

        conn.close()


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():

    if "user_id" in session:

        return redirect(url_for("dashboard"))

    return render_template("index.html")


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()

        age_input = request.form.get("age", "").strip()

        gender = request.form.get("gender", "").strip()

        occupation = request.form.get("occupation", "").strip()

        email = request.form.get("email", "").strip().lower()

        phone = request.form.get("phone", "").strip()

        password = request.form.get("password", "")

        if not name or not email or not password:

            flash("Name, email aur password required hain.")

            return redirect(url_for("register"))

        if len(password) < 8:

            flash("Password kam se kam 8 characters ka hona chahiye.")

            return redirect(url_for("register"))

        age = None

        if age_input:

            try:

                age = int(age_input)

                if age < 1 or age > 120:
                    raise ValueError

            except (ValueError, TypeError):

                flash("Valid age enter karo.")

                return redirect(url_for("register"))

        conn = get_db()

        try:

            cursor = conn.execute("""

                INSERT INTO users (

                    name,
                    age,
                    gender,
                    occupation,
                    email,
                    phone,
                    password

                )

                VALUES (?, ?, ?, ?, ?, ?, ?)

            """, (

                name,
                age,
                gender,
                occupation,
                email,
                phone,
                generate_password_hash(password)

            ))

            user_id = cursor.lastrowid

            conn.execute("""

                INSERT INTO finances (user_id)

                VALUES (?)

            """, (user_id,))

            conn.commit()

            flash("Account created successfully! Ab login karo.")

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:

            conn.rollback()

            flash("Ye email pehle se registered hai.")

            return redirect(url_for("register"))

        finally:

            conn.close()

    return render_template("register.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET" and "user_id" in session:

        return redirect_after_login("dashboard")

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()

        password = request.form.get("password", "")

        conn = get_db()

        try:

            user = conn.execute("""

                SELECT *

                FROM users

                WHERE email = ?

            """, (email,)).fetchone()

        finally:

            conn.close()

        if user and check_password_hash(user["password"], password):

            session.clear()

            session["user_id"] = user["id"]

            session["user_name"] = user["name"]

            return redirect_after_login("dashboard")

        flash("Email ya password galat hai.")

        next_page = request.args.get("next", "").strip()

        if is_safe_redirect(next_page):

            return redirect(
                url_for("login", next=next_page)
            )

        return redirect(url_for("login"))

    return render_template("login.html")


# =========================================================
# USER PROFILE
# =========================================================

@app.route("/profile", methods=["GET", "POST"])
def profile():

    if "user_id" not in session:

        return redirect(
            url_for("login", next=url_for("profile"))
        )

    user_id = session["user_id"]

    conn = get_db()

    try:

        if request.method == "POST":

            name = request.form.get("name", "").strip()

            age_input = request.form.get("age", "").strip()

            gender = request.form.get("gender", "").strip()

            occupation = request.form.get("occupation", "").strip()

            email = request.form.get("email", "").strip().lower()

            phone = request.form.get("phone", "").strip()

            photo = request.files.get("profile_photo")

            if not name or not email:

                flash("Name aur email required hain.")

                return redirect(url_for("profile"))

            age = None

            if age_input:

                try:

                    age = int(age_input)

                    if age < 1 or age > 120:
                        raise ValueError

                except (ValueError, TypeError):

                    flash("Valid age enter karo.")

                    return redirect(url_for("profile"))

            current_user = conn.execute("""

                SELECT profile_photo

                FROM users

                WHERE id = ?

            """, (user_id,)).fetchone()

            if current_user is None:

                session.clear()

                return redirect(url_for("login"))

            old_photo = current_user["profile_photo"]

            new_filename = None

            new_photo_path = None

            # IMAGE UPLOAD

            if photo and photo.filename:

                if not allowed_image(photo):

                    flash(
                        "Only valid JPG, JPEG, PNG and WEBP images allowed hain."
                    )

                    return redirect(url_for("profile"))

                extension = photo.filename.rsplit(".", 1)[1].lower()

                new_filename = (
                    str(uuid.uuid4()) + "." + extension
                )

                new_photo_path = os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    new_filename
                )

                photo.save(new_photo_path)

            try:

                if new_filename:

                    conn.execute("""

                        UPDATE users

                        SET

                            name = ?,
                            age = ?,
                            gender = ?,
                            occupation = ?,
                            email = ?,
                            phone = ?,
                            profile_photo = ?

                        WHERE id = ?

                    """, (

                        name,
                        age,
                        gender,
                        occupation,
                        email,
                        phone,
                        new_filename,
                        user_id

                    ))

                else:

                    conn.execute("""

                        UPDATE users

                        SET

                            name = ?,
                            age = ?,
                            gender = ?,
                            occupation = ?,
                            email = ?,
                            phone = ?

                        WHERE id = ?

                    """, (

                        name,
                        age,
                        gender,
                        occupation,
                        email,
                        phone,
                        user_id

                    ))

                conn.commit()

                session["user_name"] = name

                # Delete old image after successful update

                if new_filename and old_photo:

                    old_path = os.path.join(
                        app.config["UPLOAD_FOLDER"],
                        os.path.basename(old_photo)
                    )

                    if os.path.isfile(old_path):

                        os.remove(old_path)

                flash("Profile successfully update ho gayi!")

                return redirect(url_for("profile"))

            except sqlite3.IntegrityError:

                conn.rollback()

                if new_photo_path and os.path.exists(new_photo_path):

                    os.remove(new_photo_path)

                flash(
                    "Ye email kisi doosre account par registered hai."
                )

                return redirect(url_for("profile"))

            except Exception:

                conn.rollback()

                if new_photo_path and os.path.exists(new_photo_path):

                    os.remove(new_photo_path)

                raise

        user = conn.execute("""

            SELECT

                id,
                name,
                age,
                gender,
                occupation,
                email,
                phone,
                profile_photo

            FROM users

            WHERE id = ?

        """, (user_id,)).fetchone()

    finally:

        conn.close()

    if user is None:

        session.clear()

        return redirect(url_for("login"))

    return render_template(
        "profile.html",
        user=user
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:

        return redirect(
            url_for("login", next=url_for("dashboard"))
        )

    user_id = session["user_id"]

    today = date.today().isoformat()

    conn = get_db()

    try:

        user = conn.execute("""

            SELECT name

            FROM users

            WHERE id = ?

        """, (user_id,)).fetchone()

        if user is None:

            session.clear()

            return redirect(url_for("login"))

        session["user_name"] = user["name"]

        print("DASHBOARD USER NAME:", user["name"])

        finance = conn.execute("""

            SELECT monthly_income

            FROM finances

            WHERE user_id = ?

        """, (user_id,)).fetchone()

        income = (
            float(finance["monthly_income"] or 0)
            if finance else 0.0
        )

        budget_row = conn.execute("""

            SELECT amount

            FROM daily_budgets

            WHERE user_id = ?

            AND budget_date = ?

        """, (user_id, today)).fetchone()

        daily_budget = (
            float(budget_row["amount"])
            if budget_row else 0.0
        )

        expenses = conn.execute("""

            SELECT *

            FROM expenses

            WHERE user_id = ?

            ORDER BY expense_date DESC, id DESC

        """, (user_id,)).fetchall()

        total_month = conn.execute("""

            SELECT COALESCE(SUM(amount), 0)

            FROM expenses

            WHERE user_id = ?

            AND strftime('%Y-%m', expense_date) = ?

        """, (

            user_id,
            date.today().strftime("%Y-%m")

        )).fetchone()[0]

        total_month = float(total_month or 0)

        needs_budget = income * 0.50

        wants_budget = income * 0.30

        savings_budget = income * 0.20

        remaining_income = income - total_month

        expense_percentage = (
            (total_month / income) * 100
            if income > 0 else 0
        )

        expense_progress = min(
            max(expense_percentage, 0),
            100
        )

        total_today = conn.execute("""

            SELECT COALESCE(SUM(amount), 0)

            FROM expenses

            WHERE user_id = ?

            AND expense_date = ?

        """, (user_id, today)).fetchone()[0]

        total_today = float(total_today or 0)

        history = conn.execute("""

            SELECT

                expense_date,
                SUM(amount) AS total

            FROM expenses

            WHERE user_id = ?

            GROUP BY expense_date

            ORDER BY expense_date DESC

        """, (user_id,)).fetchall()

    finally:

        conn.close()

    return render_template(

        "dashboard.html",

        name=session["user_name"],

        income=income,

        total_month=total_month,

        total_today=total_today,

        expenses=expenses,

        history=history,

        today=today,

        daily_budget=daily_budget,

        daily_budget_left=daily_budget - total_today,

        needs_budget=needs_budget,

        wants_budget=wants_budget,

        savings_budget=savings_budget,

        remaining_income=remaining_income,

        expense_percentage=expense_percentage,

        expense_progress=expense_progress

    )


# =========================================================
# SET MONTHLY INCOME
# =========================================================

@app.route("/set-income", methods=["POST"])
def set_income():

    if "user_id" not in session:

        return redirect(
            url_for("login", next=url_for("dashboard"))
        )

    try:

        income = float(
            request.form.get("monthly_income", "")
        )

        if not math.isfinite(income) or income < 0:

            raise ValueError

    except (ValueError, TypeError):

        flash("Valid monthly income enter karo.")

        return redirect(url_for("dashboard"))

    conn = get_db()

    try:

        conn.execute("""

            INSERT INTO finances (

                user_id,
                monthly_income

            )

            VALUES (?, ?)

            ON CONFLICT(user_id)

            DO UPDATE SET

                monthly_income = excluded.monthly_income

        """, (

            session["user_id"],
            income

        ))

        conn.commit()

    finally:

        conn.close()

    flash("Monthly income successfully update ho gayi!")

    return redirect(url_for("dashboard"))


# =========================================================
# SET DAILY BUDGET
# =========================================================

@app.route("/set-daily-budget", methods=["POST"])
def set_daily_budget():

    if "user_id" not in session:

        return redirect(
            url_for("login", next=url_for("dashboard"))
        )

    budget_date = request.form.get(
        "budget_date",
        date.today().isoformat()
    )

    try:

        amount = float(
            request.form.get("daily_budget", "")
        )

        parsed_date = date.fromisoformat(budget_date)

        if not math.isfinite(amount) or amount < 0:

            raise ValueError

        if parsed_date < date.today():

            raise ValueError

    except (ValueError, TypeError):

        flash("Valid date aur daily budget amount enter karo.")

        return redirect(url_for("dashboard"))

    conn = get_db()

    try:

        conn.execute("""

            INSERT INTO daily_budgets (

                user_id,
                budget_date,
                amount

            )

            VALUES (?, ?, ?)

            ON CONFLICT(user_id, budget_date)

            DO UPDATE SET

                amount = excluded.amount

        """, (

            session["user_id"],
            budget_date,
            amount

        ))

        conn.commit()

    finally:

        conn.close()

    flash("Daily budget successfully save ho gaya!")

    return redirect(url_for("dashboard"))


# =========================================================
# ADD EXPENSE
# =========================================================

@app.route("/add-expense", methods=["POST"])
def add_expense():

    if "user_id" not in session:

        return redirect(
            url_for("login", next=url_for("dashboard"))
        )

    title = request.form.get("title", "").strip()

    category = (
        request.form.get("category", "Other").strip()
        or "Other"
    )

    expense_date = request.form.get(
        "expense_date",
        date.today().isoformat()
    )

    try:

        amount = float(
            request.form.get("amount", "")
        )

        parsed_date = date.fromisoformat(expense_date)

        if (
            not math.isfinite(amount)
            or amount <= 0
            or not title
        ):

            raise ValueError

    except (ValueError, TypeError):

        flash("Expense ka naam, valid amount aur date enter karo.")

        return redirect(url_for("dashboard"))

    if parsed_date > date.today():

        flash("Future date ka expense add nahi kar sakte.")

        return redirect(url_for("dashboard"))

    conn = get_db()

    try:

        conn.execute("""

            INSERT INTO expenses (

                user_id,
                title,
                amount,
                category,
                expense_date

            )

            VALUES (?, ?, ?, ?, ?)

        """, (

            session["user_id"],
            title,
            amount,
            category,
            expense_date

        ))

        conn.commit()

    finally:

        conn.close()

    flash("Expense successfully save ho gaya!")

    return redirect(url_for("dashboard"))

# =========================================================
# MONTHLY FINANCIAL ANALYTICS
# =========================================================

@app.route("/analytics")
def analytics():

    if "user_id" not in session:

        return redirect(
            url_for(
                "login",
                next=url_for("analytics")
            )
        )

    user_id = session["user_id"]

    today = date.today()

    current_month = today.strftime("%Y-%m")

    conn = get_db()

    try:

        # MONTHLY INCOME

        finance = conn.execute("""

            SELECT monthly_income

            FROM finances

            WHERE user_id = ?

        """, (user_id,)).fetchone()

        monthly_income = (
            float(finance["monthly_income"] or 0)
            if finance else 0.0
        )

        # CURRENT MONTH EXPENSE

        current_expense = conn.execute("""

            SELECT COALESCE(SUM(amount), 0)

            FROM expenses

            WHERE user_id = ?

            AND strftime('%Y-%m', expense_date) = ?

        """, (user_id, current_month)).fetchone()[0]

        current_expense = float(current_expense or 0)

        remaining_balance = monthly_income - current_expense

        savings_percentage = (
            (remaining_balance / monthly_income) * 100
            if monthly_income > 0 else 0
        )

        # CATEGORY-WISE EXPENSE

        category_rows = conn.execute("""

            SELECT

                category,

                SUM(amount) AS total

            FROM expenses

            WHERE user_id = ?

            AND strftime('%Y-%m', expense_date) = ?

            GROUP BY category

            ORDER BY total DESC

        """, (user_id, current_month)).fetchall()

        category_labels = [
            row["category"] or "Other"
            for row in category_rows
        ]

        category_amounts = [
            float(row["total"] or 0)
            for row in category_rows
        ]

        # LAST 6 MONTHS EXPENSES

        monthly_labels = []

        monthly_expenses = []

        for i in range(5, -1, -1):

            month_date = (
                today.replace(day=1)
            )

            month_number = month_date.month - i

            year = month_date.year

            while month_number <= 0:

                month_number += 12

                year -= 1

            selected_month = date(
                year,
                month_number,
                1
            )

            month_key = selected_month.strftime("%Y-%m")

            month_label = selected_month.strftime("%b %Y")

            result = conn.execute("""

                SELECT COALESCE(SUM(amount), 0)

                FROM expenses

                WHERE user_id = ?

                AND strftime('%Y-%m', expense_date) = ?

            """, (user_id, month_key)).fetchone()[0]

            monthly_labels.append(month_label)

            monthly_expenses.append(float(result or 0))

        # INCOME VS EXPENSE

        income_labels = ["Income", "Expenses", "Remaining"]

        income_values = [

            monthly_income,

            current_expense,

            max(remaining_balance, 0)

        ]

        # TOTAL EXPENSE RECORDS

        total_transactions = conn.execute("""

            SELECT COUNT(*)

            FROM expenses

            WHERE user_id = ?

            AND strftime('%Y-%m', expense_date) = ?

        """, (user_id, current_month)).fetchone()[0]

        # HIGHEST SPENDING CATEGORY

        highest_category = (
            category_labels[0]
            if category_labels else "No Expenses"
        )

    finally:

        conn.close()

    return render_template(

        "analytics.html",

        name=session.get("user_name", "User"),

        monthly_income=monthly_income,

        current_expense=current_expense,

        remaining_balance=remaining_balance,

        savings_percentage=savings_percentage,

        category_labels=category_labels,

        category_amounts=category_amounts,

        monthly_labels=monthly_labels,

        monthly_expenses=monthly_expenses,

        income_labels=income_labels,

        income_values=income_values,

        total_transactions=total_transactions,

        highest_category=highest_category

    )
# =========================================================
# SAVINGS GOALS
# =========================================================

@app.route("/savings-goals", methods=["GET", "POST"])
def savings_goals():

    if "user_id" not in session:

        return redirect(
            url_for(
                "login",
                next=url_for("savings_goals")
            )
        )

    user_id = session["user_id"]

    conn = get_db()

    try:

        # CREATE NEW SAVINGS GOAL

        if request.method == "POST":

            title = request.form.get(
                "title", ""
            ).strip()

            target_date = request.form.get(
                "target_date", ""
            ).strip()

            try:

                target_amount = float(
                    request.form.get("target_amount", "")
                )

                if (
                    not math.isfinite(target_amount)
                    or target_amount <= 0
                    or not title
                ):
                    raise ValueError

                if target_date:
                    date.fromisoformat(target_date)

            except (ValueError, TypeError):

                flash(
                    "Valid goal name, target amount aur date enter karo."
                )

                return redirect(url_for("savings_goals"))

            conn.execute("""

                INSERT INTO savings_goals (

                    user_id,
                    title,
                    target_amount,
                    saved_amount,
                    target_date

                )

                VALUES (?, ?, ?, 0, ?)

            """, (

                user_id,
                title,
                target_amount,
                target_date or None

            ))

            conn.commit()

            flash("New savings goal successfully created!")

            return redirect(url_for("savings_goals"))

        # FETCH ALL GOALS

        goals = conn.execute("""

            SELECT *

            FROM savings_goals

            WHERE user_id = ?

            ORDER BY created_at DESC

        """, (user_id,)).fetchall()

        goal_list = []

        total_target = 0

        total_saved = 0

        completed_goals = 0

        for goal in goals:

            target = float(goal["target_amount"] or 0)

            saved = float(goal["saved_amount"] or 0)

            progress = (
                min((saved / target) * 100, 100)
                if target > 0 else 0
            )

            remaining = max(target - saved, 0)

            is_completed = saved >= target

            if is_completed:
                completed_goals += 1

            total_target += target

            total_saved += saved

            goal_list.append({

                "id": goal["id"],

                "title": goal["title"],

                "target_amount": target,

                "saved_amount": saved,

                "target_date": goal["target_date"],

                "progress": round(progress, 1),

                "remaining": remaining,

                "is_completed": is_completed

            })

    finally:

        conn.close()

    overall_progress = (
        min((total_saved / total_target) * 100, 100)
        if total_target > 0 else 0
    )

    return render_template(

        "savings.html",

        name=session.get("user_name", "User"),

        goals=goal_list,

        total_target=total_target,

        total_saved=total_saved,

        total_remaining=max(total_target - total_saved, 0),

        completed_goals=completed_goals,

        total_goals=len(goal_list),

        overall_progress=round(overall_progress, 1)

    )


# =========================================================
# ADD MONEY TO SAVINGS GOAL
# =========================================================

@app.route(
    "/savings-goals/<int:goal_id>/add",
    methods=["POST"]
)
def add_goal_savings(goal_id):

    if "user_id" not in session:

        return redirect(url_for("login"))

    user_id = session["user_id"]

    try:

        amount = float(
            request.form.get("amount", "")
        )

        if not math.isfinite(amount) or amount <= 0:

            raise ValueError

    except (ValueError, TypeError):

        flash("Valid savings amount enter karo.")

        return redirect(url_for("savings_goals"))

    conn = get_db()

    try:

        goal = conn.execute("""

            SELECT *

            FROM savings_goals

            WHERE id = ?

            AND user_id = ?

        """, (

            goal_id,
            user_id

        )).fetchone()

        if goal is None:

            flash("Savings goal nahi mila.")

            return redirect(url_for("savings_goals"))

        remaining = (
            float(goal["target_amount"])
            - float(goal["saved_amount"])
        )

        if amount > remaining:

            flash(
                f"Is goal mein sirf ₹{max(remaining, 0):,.2f} add kar sakte ho."
            )

            return redirect(url_for("savings_goals"))

        conn.execute("""

            UPDATE savings_goals

            SET saved_amount = saved_amount + ?

            WHERE id = ?

            AND user_id = ?

        """, (

            amount,
            goal_id,
            user_id

        ))

        conn.commit()

        flash("Savings successfully add ho gayi!")

    finally:

        conn.close()

    return redirect(url_for("savings_goals"))


# =========================================================
# DELETE SAVINGS GOAL
# =========================================================

@app.route(
    "/savings-goals/<int:goal_id>/delete",
    methods=["POST"]
)
def delete_savings_goal(goal_id):

    if "user_id" not in session:

        return redirect(url_for("login"))

    conn = get_db()

    try:

        cursor = conn.execute("""

            DELETE FROM savings_goals

            WHERE id = ?

            AND user_id = ?

        """, (

            goal_id,
            session["user_id"]

        ))

        conn.commit()

        if cursor.rowcount > 0:

            flash("Savings goal successfully deleted!")

        else:

            flash("Savings goal nahi mila.")

    finally:

        conn.close()

    return redirect(url_for("savings_goals"))
# =========================================================
# PAISAFLOW AI CHAT
# =========================================================
# =========================================================
# PAISAFLOW AI CHAT
# =========================================================

@app.route("/api/chat", methods=["POST"])
def chat():

    # User login check
    if "user_id" not in session:
        return {
            "reply": "Please log in to use PaisaFlow AI."
        }, 401

    # Request JSON check
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()

    if not message:
        return {
            "reply": "Please enter a message."
        }, 400

    if len(message) > 2000:
        return {
            "reply": "Your message is too long. Please keep it under 2000 characters."
        }, 400

    if not GEMINI_API_KEY:
        return {
            "reply": "Gemini API key is not configured."
        }, 500

    user_id = session["user_id"]

    # Fetch user's financial data
    conn = get_db()

    try:
        finance = conn.execute("""
            SELECT monthly_income
            FROM finances
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        monthly_income = (
            float(finance["monthly_income"] or 0)
            if finance else 0.0
        )

        current_month = date.today().strftime("%Y-%m")

        expense_result = conn.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM expenses
            WHERE user_id = ?
            AND strftime('%Y-%m', expense_date) = ?
        """, (user_id, current_month)).fetchone()

        monthly_expenses = float(expense_result[0] or 0)

        today = date.today().isoformat()

        today_result = conn.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM expenses
            WHERE user_id = ?
            AND expense_date = ?
        """, (user_id, today)).fetchone()

        spent_today = float(today_result[0] or 0)

        budget_result = conn.execute("""
            SELECT amount
            FROM daily_budgets
            WHERE user_id = ?
            AND budget_date = ?
        """, (user_id, today)).fetchone()

        daily_budget = (
            float(budget_result["amount"])
            if budget_result else 0.0
        )

    finally:
        conn.close()

    # Build prompt
    prompt = f"""
You are PaisaFlow AI, a friendly personal finance assistant.

Answer the user's financial questions in simple language.
Use Indian Rupees (₹) for money.
Keep answers helpful and reasonably brief.
Do not invent financial data.
Do not claim to be a certified financial advisor.

User's financial data:
- Monthly income: ₹{monthly_income:,.2f}
- Expenses this month: ₹{monthly_expenses:,.2f}
- Remaining income this month: ₹{monthly_income - monthly_expenses:,.2f}
- Spent today: ₹{spent_today:,.2f}
- Today's budget: ₹{daily_budget:,.2f}

User's question:
{message}
"""

    # Gemini REST API configuration
    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/models/gemini-3.1-flash-lite:generateContent"
    )

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "maxOutputTokens": 500
        }
    }

    try:
        # Retry up to 3 times if Gemini is temporarily overloaded
        response = None

        for attempt in range(3):
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=(10, 60)
            )

            if response.status_code != 503:
                break

            if attempt < 2:
                time.sleep(2 * (attempt + 1))

        # Check Gemini response
        if response.status_code != 200:
            print(
                "Gemini API Error:",
                response.status_code,
                response.text[:1000]
            )

            return {
                "reply": "I'm having trouble responding right now. Please try again in a little while."
            }, 502

        result = response.json()

        reply = (
            result["candidates"][0]["content"]["parts"][0]["text"]
        )

        return {
            "reply": reply
        }

    except requests.exceptions.Timeout:
        return {
            "reply": "Gemini is taking too long to respond. Please try again."
        }, 504

    except requests.exceptions.RequestException as error:
        print("Gemini connection error:", error)

        return {
            "reply": "Unable to connect to Gemini right now."
        }, 502

    except (KeyError, IndexError, TypeError):
        return {
            "reply": "Gemini returned an unexpected response. Please try again."
        }, 502
# =========================================================
# FINANCIAL CALCULATORS
# =========================================================

@app.route("/calculators")
def calculators():

    if "user_id" not in session:
        return redirect(
            url_for(
                "login",
                next=url_for("calculators")
            )
        )

    return render_template(
        "calculators.html",
        name=session.get("user_name", "User")
    )




# =========================================================
# NEARBY ATM FINDER
# =========================================================

@app.route("/atm-finder")
def atm_finder():
    if "user_id" not in session:
        return redirect(
            url_for(
                "login",
                next=url_for("atm_finder")
            )
        )

    return render_template(
        "atm_finder.html",
        name=session.get("user_name", "User")
    )

# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# =========================================================
# EXPLORE INVESTMENTS
# =========================================================

@app.route("/explore-investments")
def explore_investments():

    if "user_id" not in session:

        return redirect(
            url_for(
                "login",
                next=url_for("explore_investments")
            )
        )

    return render_template("explore_investments.html")


# =========================================================
# SMART SAVINGS & INVESTMENT HUB
# =========================================================

@app.route("/investment")
def investment():

    if "user_id" not in session:

        return redirect(
            url_for(
                "login",
                next=url_for("investment")
            )
        )

    user_id = session["user_id"]

    conn = get_db()

    try:

        finance = conn.execute("""

            SELECT monthly_income

            FROM finances

            WHERE user_id = ?

        """, (user_id,)).fetchone()

        income = (
            float(finance["monthly_income"] or 0)
            if finance else 0.0
        )

        expense_result = conn.execute("""

            SELECT COALESCE(SUM(amount), 0) AS total

            FROM expenses

            WHERE user_id = ?

            AND strftime('%Y-%m', expense_date) = ?

        """, (

            user_id,
            date.today().strftime("%Y-%m")

        )).fetchone()

        total_expenses = float(
            expense_result["total"] or 0
        )

        remaining_balance = income - total_expenses

        savings_budget = income * 0.20

    finally:

        conn.close()

    return render_template(

        "investment.html",

        name=session.get("user_name", "User"),

        income=income,

        total_expenses=total_expenses,

        remaining_balance=remaining_balance,

        savings_budget=savings_budget

    )


# =========================================================
# CALENDAR ANALYTICS
# =========================================================

@app.route("/calendar")
def calendar():

    if "user_id" not in session:

        return redirect(
            url_for(
                "login",
                next=url_for("calendar")
            )
        )

    user_id = session["user_id"]

    conn = get_db()

    try:

        finance = conn.execute("""

            SELECT monthly_income

            FROM finances

            WHERE user_id = ?

        """, (user_id,)).fetchone()

        monthly_income = (
            float(finance["monthly_income"] or 0)
            if finance else 0.0
        )

        expenses = conn.execute("""

            SELECT

                id,
                title,
                amount,
                category,
                expense_date

            FROM expenses

            WHERE user_id = ?

            ORDER BY expense_date DESC, id DESC

        """, (user_id,)).fetchall()

        expense_data = []

        for expense in expenses:

            expense_data.append({

                "id": expense["id"],

                "title": expense["title"],

                "amount": float(expense["amount"] or 0),

                "category": expense["category"] or "Other",

                "date": expense["expense_date"]

            })

    finally:

        conn.close()

    return render_template(

        "calendar.html",

        name=session.get("user_name", "User"),

        today=date.today().isoformat(),

        monthly_income=monthly_income,

        expense_data=expense_data

    )


# =========================================================
# DAILY EXPENSE ANALYSIS
# =========================================================

@app.route("/calendar/day/<selected_date>")
def daily_expense_analysis(selected_date):

    if "user_id" not in session:

        return redirect(
            url_for(
                "login",
                next=url_for(
                    "daily_expense_analysis",
                    selected_date=selected_date
                )
            )
        )

    user_id = session["user_id"]

    try:

        selected_day = date.fromisoformat(selected_date)

    except ValueError:

        flash("Invalid date selected.")

        return redirect(url_for("calendar"))

    selected_date = selected_day.isoformat()

    conn = get_db()

    try:

        daily_rows = conn.execute("""

            SELECT

                id,
                title,
                amount,
                category,
                expense_date

            FROM expenses

            WHERE user_id = ?

            AND expense_date = ?

            ORDER BY amount DESC, id DESC

        """, (

            user_id,
            selected_date

        )).fetchall()

        expense_data = []

        for row in daily_rows:

            expense_data.append({

                "id": row["id"],

                "title": row["title"],

                "amount": float(row["amount"] or 0),

                "category": row["category"] or "Other",

                "expense_date": row["expense_date"]

            })

        finance = conn.execute("""

            SELECT monthly_income

            FROM finances

            WHERE user_id = ?

        """, (user_id,)).fetchone()

        monthly_income = (
            float(finance["monthly_income"] or 0)
            if finance else 0.0
        )

        monthly_rows = conn.execute("""

            SELECT

                expense_date,
                amount,
                title,
                category

            FROM expenses

            WHERE user_id = ?

            AND strftime('%Y-%m', expense_date) = ?

            ORDER BY expense_date, id

        """, (

            user_id,
            selected_date[:7]

        )).fetchall()

        monthly_expenses = []

        for row in monthly_rows:

            monthly_expenses.append({

                "expense_date": row["expense_date"],

                "amount": float(row["amount"] or 0),

                "title": row["title"],

                "category": row["category"] or "Other"

            })

        daily_total = sum(
            item["amount"] for item in expense_data
        )

        monthly_total = sum(
            item["amount"] for item in monthly_expenses
        )

        remaining_income = monthly_income - monthly_total

        selected_date_label = selected_day.strftime(
            "%A, %d %B %Y"
        )

    finally:

        conn.close()

    return render_template(

        "daily_analysis.html",

        name=session.get("user_name", "User"),

        selected_date=selected_date,

        selected_date_label=selected_date_label,

        expense_data=expense_data,

        daily_total=daily_total,

        monthly_income=monthly_income,

        monthly_total=monthly_total,

        remaining_income=remaining_income,

        monthly_expenses=monthly_expenses

    )


# =========================================================
# FILE SIZE ERROR
# =========================================================

@app.errorhandler(413)
def file_too_large(error):

    flash("Image size 5 MB se kam honi chahiye.")

    return redirect(url_for("profile"))


# =========================================================
# START APPLICATION
# =========================================================

init_db()

if __name__ == "__main__":

    app.run(debug=True)