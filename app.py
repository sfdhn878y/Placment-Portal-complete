from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "college-project-secret"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///placement.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# =====================
# MODELS
# =====================

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    # admin / student / company
    role = db.Column(db.String(20), nullable=False)

    # company approval
    is_approved = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student_profile = db.relationship(
        "StudentProfile", back_populates="user",
    )
    
    company_profile = db.relationship(
        "CompanyProfile", back_populates="user", 
    )


class StudentProfile(db.Model):
    __tablename__ = "student_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    department = db.Column(db.String(100))
    cgpa = db.Column(db.Float)
    resume = db.Column(db.String(200))

    user = db.relationship("User", back_populates="student_profile")
    applications = db.relationship("Application", back_populates="student")


class CompanyProfile(db.Model):
    __tablename__ = "company_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    company_name = db.Column(db.String(150))
    industry = db.Column(db.String(100))
    website = db.Column(db.String(150))

    description = db.Column(db.Text)
    location = db.Column(db.String(100))
    company_size = db.Column(db.String(50))

    user = db.relationship("User", back_populates="company_profile")
    jobs = db.relationship("Job", back_populates="company")


class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company_profiles.id"))

    title = db.Column(db.String(150))
    skills = db.Column(db.String(200))
    salary = db.Column(db.String(50))
    is_approved = db.Column(db.Boolean, default=False)

    company = db.relationship("CompanyProfile", back_populates="jobs")
    applications = db.relationship("Application", back_populates="job")


class Application(db.Model):
    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"))
    student_id = db.Column(db.Integer, db.ForeignKey("student_profiles.id"))

    status = db.Column(db.String(50), default="Applied")
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)

    job = db.relationship("Job", back_populates="applications")
    student = db.relationship("StudentProfile", back_populates="applications")


# =====================
# ROUTES
# # =====================

@app.route("/")
def index():
    return render_template("index.html")




@app.route("/admin_dashboard")
def admin():
    return render_template("admin_dashboard.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]  # student / company

        # block admin registration
        if role == "admin":
            return "Admin cannot be registered"

        if User.query.filter_by(email=email).first():
            return "Email already registered"

        user = User(
            name=name,
            email=email,
            password=password,
            role=role,
            is_approved=False if role == "company" else True
        )

        db.session.add(user)
        db.session.commit()

        session["user_id"] = user.id
        session["role"] = user.role

        if role == "student":
            return redirect("/student/complete-profile")
        else:
            return redirect("/company/wait")

    return render_template("register.html")


@app.route("/student/complete-profile", methods=["GET", "POST"])
def student_complete_profile():
    if "user_id" not in session or session["role"] != "student":
        return redirect("/login")

    if request.method == "POST":
        profile = StudentProfile(
            user_id=session["user_id"],
            department=request.form["department"],
            cgpa=request.form["cgpa"]
        )

        db.session.add(profile)
        db.session.commit()

        return redirect("/student/dashboard")

    return render_template("student_profile.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if not user:
            print('186 line ')
            return "No user found"

        # ✅ FIXED password check
        if not (user.password, password):
            print(user.password,password)
            return "Wrong password" 
        session["user_id"] = user.id
        session["role"] = user.role
        if user.role == "company" and not user.is_approved:
            return redirect(url_for("company_wait"))



        if user.role == "Admin":
            return redirect("/admin_dashboard")
        elif user.role == "company":
            return redirect("/company/dashboard")
        else:
            return redirect("/student/dashboard")

    return render_template("login.html")



@app.route("/company/wait")
def company_wait():
    # user must be logged in
    if "user_id" not in session:
        print('user not is session')
        return redirect("/login")

    # only for companies
    if session.get("role") != "company":
        return redirect("/login")

    user = User.query.get(session["user_id"])

    # if already approved, go straight to dashboard
    if user.is_approved:
        return redirect("/company/dashboard")

    return render_template("company_wait.html")



@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")



@app.route("/company/dashboard")
def company_dashboard():
    if "user_id" not in session or session["role"] != "company":
        return redirect("/login")

    company = CompanyProfile.query.filter_by(
        user_id=session["user_id"]
    ).first()

    jobs = []
    if company:
        jobs = Job.query.filter_by(company_id=company.id).all()

    return render_template(
        "company_dashboard.html",
        company=company,
        jobs=jobs
    )
    
@app.route("/company/create-profile", methods=["GET", "POST"])
def company_create_profile():
    if "user_id" not in session or session["role"] != "company":
        return redirect("/login")

    existing = CompanyProfile.query.filter_by(
        user_id=session["user_id"]
    ).first()

    if existing:
        return redirect("/company/dashboard")

    if request.method == "POST":
        profile = CompanyProfile(
            user_id=session["user_id"],
            company_name=request.form["company_name"],
            industry=request.form["industry"],
            website=request.form["website"],
            location=request.form["location"],
            company_size=request.form["company_size"],
            description=request.form["description"]
        )
        db.session.add(profile)
        db.session.commit()

        return redirect("/company/dashboard")


    return render_template("company_create_profile.html")


# =====================
# RUN
# =====================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        existing_admin = User.query.filter_by(name="admin").first()

        if not existing_admin:

            admin_db = User(
                name = 'admin',
                password ='admin',
                email = 'admin@gmail.com',
                role='Admin'
            )
            db.session.add(admin_db)
            db.session.commit()
    app.run(debug=True)