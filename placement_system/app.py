from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "replace-this-with-a-long-random-secret"

DATABASE = "placement.db"

# Expanded Modern Question Bank
QUESTIONS = [
    {
        "question": "Which language creates the structure of web pages?",
        "options": ["CSS", "HTML", "SQL", "Python"],
        "answer": 1
    },
    {
        "question": "Which data structure follows FIFO (First In, First Out)?",
        "options": ["Stack", "Queue", "Tree", "Graph"],
        "answer": 1
    },
    {
        "question": "Which SQL command retrieves records from a database?",
        "options": ["SELECT", "DELETE", "DROP", "UPDATE"],
        "answer": 0
    },
    {
        "question": "Which Python keyword defines a function?",
        "options": ["function", "define", "def", "fun"],
        "answer": 2
    },
    {
        "question": "Which CSS property changes the text color?",
        "options": ["font-style", "background", "color", "margin"],
        "answer": 2
    },
    # --- Modern Tech Questions ---
    {
        "question": "Which Git command initializes a new local repository?",
        "options": ["git start", "git init", "git new", "git create"],
        "answer": 1
    },
    {
        "question": "Which HTTP method is typically used to update an existing resource completely?",
        "options": ["GET", "POST", "PUT", "PATCH"],
        "answer": 2
    },
    {
        "question": "What is the primary tool used for containerizing applications?",
        "options": ["Kubernetes", "Docker", "Jenkins", "Ansible"],
        "answer": 1
    },
    {
        "question": "Which JavaScript library/framework was developed by Meta for building user interfaces?",
        "options": ["Angular", "Vue", "React", "Svelte"],
        "answer": 2
    },
    {
        "question": "Which of the following is a fully managed serverless compute service by AWS?",
        "options": ["Amazon EC2", "AWS Lambda", "Amazon S3", "Amazon RDS"],
        "answer": 1
    }
]


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                score INTEGER NOT NULL,
                total INTEGER NOT NULL,
                FOREIGN KEY(student_id) REFERENCES students(id)
            )
        """)


def login_required():
    return "student_id" in session


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    message = ""

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or "@" not in email or len(password) < 6:
            message = "Enter valid details and a password of at least 6 characters."
        else:
            try:
                with get_db() as conn:
                    conn.execute(
                        "INSERT INTO students (name, email, password) VALUES (?, ?, ?)",
                        (name, email, generate_password_hash(password))
                    )
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                message = "This email is already registered."

    return render_template("register.html", message=message)


@app.route("/login", methods=["GET", "POST"])
def login():
    message = ""

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with get_db() as conn:
            student = conn.execute(
                "SELECT * FROM students WHERE email = ?", (email,)
            ).fetchone()

        if student and check_password_hash(student["password"], password):
            session.clear()
            session["student_id"] = student["id"]
            session["student_name"] = student["name"]
            return redirect(url_for("dashboard"))

        message = "Invalid email or password."

    return render_template("login.html", message=message)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/dashboard")
def dashboard():
    if not login_required():
        return redirect(url_for("login"))

    with get_db() as conn:
        results = conn.execute(
            "SELECT score, total FROM results WHERE student_id = ? ORDER BY id DESC",
            (session["student_id"],)
        ).fetchall()

    attempts = len(results)
    average = (
        sum(r["score"] * 100 / r["total"] for r in results if r["total"]) / attempts
        if attempts else 0
    )

    return render_template(
        "dashboard.html",
        student=session["student_name"],
        attempts=attempts,
        average=average,
        results=results
    )


@app.route("/practice")
def practice():
    if not login_required():
        return redirect(url_for("login"))
    return render_template("practice.html")


@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if not login_required():
        return redirect(url_for("login"))

    if request.method == "POST":
        score = 0

        for i, question in enumerate(QUESTIONS):
            selected = request.form.get(f"answer_{i}", "")
            if selected.isdigit() and int(selected) == question["answer"]:
                score += 1

        with get_db() as conn:
            conn.execute(
                "INSERT INTO results (student_id, score, total) VALUES (?, ?, ?)",
                (session["student_id"], score, len(QUESTIONS))
            )

        session["last_score"] = score
        session["last_total"] = len(QUESTIONS)
        return redirect(url_for("result"))

    return render_template("quiz.html", questions=QUESTIONS)


@app.route("/result")
def result():
    if not login_required():
        return redirect(url_for("login"))

    if "last_score" not in session:
        return redirect(url_for("quiz"))

    return render_template(
        "result.html",
        score=session["last_score"],
        total=session["last_total"],
        student=session["student_name"]
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True)