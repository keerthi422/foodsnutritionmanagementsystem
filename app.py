from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date

app = Flask(__name__)

app.secret_key = "nutrition_secret_key"

DATABASE = "nutrition.db"


# =========================
# DATABASE
# =========================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_db()

    # Users
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user'
        )
    """)

    # Foods
    conn.execute("""
        CREATE TABLE IF NOT EXISTS foods (
            food_id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_name TEXT NOT NULL,
            category TEXT,
            calories REAL DEFAULT 0,
            protein REAL DEFAULT 0,
            carbohydrates REAL DEFAULT 0,
            fat REAL DEFAULT 0,
            fiber REAL DEFAULT 0
        )
    """)

    # Meals
    conn.execute("""
        CREATE TABLE IF NOT EXISTS meals (
            meal_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            meal_type TEXT,
            food_name TEXT,
            quantity REAL,
            calories REAL DEFAULT 0,
            protein REAL DEFAULT 0,
            carbohydrates REAL DEFAULT 0,
            fat REAL DEFAULT 0,
            fiber REAL DEFAULT 0,
            date TEXT
        )
    """)

    # BMI
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bmi_records (
            bmi_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            height REAL,
            weight REAL,
            bmi REAL,
            status TEXT
        )
    """)

    # Profile
    conn.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            full_name TEXT,
            email TEXT,
            phone TEXT,
            age INTEGER,
            gender TEXT,
            height REAL,
            weight REAL,
            goal TEXT
        )
    """)

    # Default admin
    admin = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        ("admin",)
    ).fetchone()

    if admin is None:

        password = generate_password_hash("admin123")

        conn.execute("""
            INSERT INTO users
            (username, password, role)
            VALUES (?, ?, ?)
        """, ("admin", password, "admin"))

    conn.commit()
    conn.close()


# =========================
# HOME
# =========================

@app.route("/")
def home():
    return render_template("index.html")


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    conn.close()

    if user and check_password_hash(user["password"], password):

        session["user_id"] = user["user_id"]
        session["username"] = user["username"]
        session["role"] = user["role"]

        return redirect(url_for("dashboard"))

    return render_template(
        "login.html",
        error="Invalid username or password"
    )


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    food_count = conn.execute(
        "SELECT COUNT(*) FROM foods"
    ).fetchone()[0]

    meal_count = conn.execute(
        "SELECT COUNT(*) FROM meals WHERE user_id = ?",
        (session["user_id"],)
    ).fetchone()[0]

    bmi_count = conn.execute(
        "SELECT COUNT(*) FROM bmi_records WHERE user_id = ?",
        (session["user_id"],)
    ).fetchone()[0]

    profile = conn.execute(
        "SELECT * FROM profiles WHERE user_id = ?",
        (session["user_id"],)
    ).fetchone()

    conn.close()

    return render_template(
        "dashboard.html",
        username=session["username"],
        role=session["role"],
        food_count=food_count,
        meal_count=meal_count,
        bmi_count=bmi_count,
        profile=profile
    )


# =========================
# PROFILE
# =========================

@app.route("/profile", methods=["GET", "POST"])
def profile():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    if request.method == "POST":

        full_name = request.form.get("full_name", "")
        email = request.form.get("email", "")
        phone = request.form.get("phone", "")
        age = request.form.get("age") or None
        gender = request.form.get("gender", "")
        height = request.form.get("height") or None
        weight = request.form.get("weight") or None
        goal = request.form.get("goal", "")

        existing = conn.execute(
            "SELECT * FROM profiles WHERE user_id = ?",
            (session["user_id"],)
        ).fetchone()

        if existing:

            conn.execute("""
                UPDATE profiles SET
                full_name=?,
                email=?,
                phone=?,
                age=?,
                gender=?,
                height=?,
                weight=?,
                goal=?
                WHERE user_id=?
            """, (
                full_name,
                email,
                phone,
                age,
                gender,
                height,
                weight,
                goal,
                session["user_id"]
            ))

        else:

            conn.execute("""
                INSERT INTO profiles
                (user_id, full_name, email, phone, age,
                 gender, height, weight, goal)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session["user_id"],
                full_name,
                email,
                phone,
                age,
                gender,
                height,
                weight,
                goal
            ))

        conn.commit()

    profile_data = conn.execute(
        "SELECT * FROM profiles WHERE user_id = ?",
        (session["user_id"],)
    ).fetchone()

    conn.close()

    return render_template(
        "profile.html",
        profile=profile_data
    )


# =========================
# FOODS
# =========================

@app.route("/foods")
def foods():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    foods_data = conn.execute(
        "SELECT * FROM foods ORDER BY food_id DESC"
    ).fetchall()

    conn.close()

    return render_template(
        "foods.html",
        foods=foods_data
    )


# =========================
# ADD FOOD
# =========================

@app.route("/add-food", methods=["GET", "POST"])
def add_food():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        food_name = request.form.get("food_name", "")
        category = request.form.get("category", "")

        calories = float(request.form.get("calories") or 0)
        protein = float(request.form.get("protein") or 0)
        carbohydrates = float(
            request.form.get("carbohydrates") or 0
        )
        fat = float(request.form.get("fat") or 0)
        fiber = float(request.form.get("fiber") or 0)

        conn = get_db()

        conn.execute("""
            INSERT INTO foods
            (food_name, category, calories, protein,
             carbohydrates, fat, fiber)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            food_name,
            category,
            calories,
            protein,
            carbohydrates,
            fat,
            fiber
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("foods"))

    return render_template("add_food.html")


# =========================
# DELETE FOOD
# =========================

@app.route("/delete-food/<int:food_id>")
def delete_food(food_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    conn.execute(
        "DELETE FROM foods WHERE food_id = ?",
        (food_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("foods"))


# =========================
# BMI CALCULATOR
# =========================

@app.route("/bmi", methods=["GET", "POST"])
def bmi():

    if "user_id" not in session:
        return redirect(url_for("login"))

    bmi_value = None
    status = None

    if request.method == "POST":

        try:

            height = float(request.form.get("height"))
            weight = float(request.form.get("weight"))

            if height <= 0 or weight <= 0:
                raise ValueError

            height_m = height / 100

            bmi_value = weight / (height_m ** 2)

            bmi_value = round(bmi_value, 2)

            if bmi_value < 18.5:
                status = "Underweight"

            elif bmi_value < 25:
                status = "Normal Weight"

            elif bmi_value < 30:
                status = "Overweight"

            else:
                status = "Obese"

            conn = get_db()

            conn.execute("""
                INSERT INTO bmi_records
                (user_id, height, weight, bmi, status)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session["user_id"],
                height,
                weight,
                bmi_value,
                status
            ))

            conn.commit()
            conn.close()

        except:
            return render_template(
                "bmi.html",
                error="Enter valid height and weight"
            )

    conn = get_db()

    records = conn.execute("""
        SELECT * FROM bmi_records
        WHERE user_id = ?
        ORDER BY bmi_id DESC
    """, (
        session["user_id"],
    )).fetchall()

    conn.close()

    return render_template(
        "bmi.html",
        bmi_value=bmi_value,
        status=status,
        records=records
    )


# =========================
# CALORIE CALCULATOR
# =========================

@app.route(
    "/calorie-calculator",
    methods=["GET", "POST"]
)
def calorie_calculator():

    if "user_id" not in session:
        return redirect(url_for("login"))

    bmr = None
    calories = None

    if request.method == "POST":

        try:

            age = int(request.form.get("age"))
            gender = request.form.get("gender")
            height = float(request.form.get("height"))
            weight = float(request.form.get("weight"))
            activity = request.form.get(
                "activity",
                "sedentary"
            )

            if gender == "male":

                bmr = (
                    10 * weight
                    + 6.25 * height
                    - 5 * age
                    + 5
                )

            else:

                bmr = (
                    10 * weight
                    + 6.25 * height
                    - 5 * age
                    - 161
                )

            activity_rate = {
                "sedentary": 1.2,
                "light": 1.375,
                "moderate": 1.55,
                "active": 1.725,
                "very_active": 1.9
            }

            calories = bmr * activity_rate.get(
                activity,
                1.2
            )

            bmr = round(bmr)
            calories = round(calories)

        except:
            return render_template(
                "calorie_calculator.html",
                error="Enter valid information"
            )

    return render_template(
        "calorie_calculator.html",
        bmr=bmr,
        calories=calories
    )


# =========================
# ALIAS
# =========================
# This prevents the previous
# calorie_calculator BuildError.

@app.route("/calorie")
def calorie():

    return redirect(
        url_for("calorie_calculator")
    )


# =========================
# MEALS
# =========================

@app.route("/meals")
def meals():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    meals_data = conn.execute("""
        SELECT * FROM meals
        WHERE user_id = ?
        ORDER BY meal_id DESC
    """, (
        session["user_id"],
    )).fetchall()

    total_calories = conn.execute("""
        SELECT COALESCE(SUM(calories), 0)
        FROM meals
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()[0]

    conn.close()

    return render_template(
        "meals.html",
        meals=meals_data,
        total_calories=total_calories,
        meal_count=len(meals_data),
        username=session["username"]
    )


# =========================
# ADD MEAL
# =========================

@app.route("/add-meal", methods=["GET", "POST"])
def add_meal():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        meal_type = request.form.get("meal_type", "")
        food_name = request.form.get("food_name", "")
        quantity = float(
            request.form.get("quantity") or 1
        )

        calories = float(
            request.form.get("calories") or 0
        )

        protein = float(
            request.form.get("protein") or 0
        )

        carbohydrates = float(
            request.form.get("carbohydrates") or 0
        )

        fat = float(
            request.form.get("fat") or 0
        )

        fiber = float(
            request.form.get("fiber") or 0
        )

        meal_date = request.form.get(
            "date",
            str(date.today())
        )

        conn = get_db()

        conn.execute("""
            INSERT INTO meals
            (user_id, meal_type, food_name, quantity,
             calories, protein, carbohydrates, fat,
             fiber, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            meal_type,
            food_name,
            quantity,
            calories,
            protein,
            carbohydrates,
            fat,
            fiber,
            meal_date
        ))

        conn.commit()
        conn.close()

        return redirect(url_for("meals"))

    return render_template("add_meal.html")


# =========================
# REPORTS
# =========================

# =========================================================
# NUTRITION REPORTS
# =========================================================

@app.route("/reports", endpoint="reports")
@app.route("/nutrition-reports")
def nutrition_reports():

    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    conn = get_db()

    total_meals = conn.execute(
        """
        SELECT COUNT(*)
        FROM meals
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()[0]

    total_calories = conn.execute(
        """
        SELECT COALESCE(SUM(calories), 0)
        FROM meals
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()[0]

    total_bmi = conn.execute(
        """
        SELECT COUNT(*)
        FROM bmi_records
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()[0]

    conn.close()

    return render_template(
        "reports.html",
        total_meals=total_meals,
        total_calories=round(total_calories, 2),
        total_bmi=total_bmi
    )


# =========================
# START APPLICATION
# =========================

init_db()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )