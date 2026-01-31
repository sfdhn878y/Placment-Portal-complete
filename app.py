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
    is_closed = db.Column(db.Boolean, default=False)  # 👈 add this

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




@app.route("/company/post-job", methods=["GET", "POST"])
def post_job():

    # basic auth check
    if "user_id" not in session or session.get("role") != "company":
        return redirect("/login")

    user = User.query.get(session["user_id"])

    # company must be approved
    if not user.is_approved:
        return "Your company is not approved yet"

    company = CompanyProfile.query.filter_by(user_id=user.id).first()

    # safety check
    if not company:
        return redirect("/company/create-profile")

    if request.method == "POST":
        title = request.form["title"]
        skills = request.form["skills"]
        salary = request.form["salary"]

        job = Job(
            title=title,
            skills=skills,
            salary=salary,
            company_id=company.id,
            is_approved=False  # admin will approve later
        )

        db.session.add(job)
        db.session.commit()

        return redirect("/company/dashboard")

    return render_template("post_job.html")




@app.route("/")
def index():
    return render_template("index.html")

@app.route("/admin_dashboard",methods=['POST','GET'])
def admin_dashboard():
    total_c = User.query.filter_by(role="company").count()
    print(total_c)
    companies = User.query.filter_by(role="company").all()


    user_id = request.args.get('user_id')
    status = request.args.get("status")



    if user_id and status:
        user = User.query.get(user_id)
        if user:
            user.is_approved = int(status)
            db.session.commit()
    return render_template("admin_dashboard.html",total_c=total_c,user_id=user_id,companies=companies)


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



@app.route("/student/dashboard")
def student_dashboard():

    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(session["user_id"])

    if not user or user.role != "student":
        return redirect("/login")

    student = StudentProfile.query.filter_by(
        user_id=user.id
    ).first()

    if not student:
        return redirect("/student/complete-profile")

    # student's applications
    applications = Application.query.filter_by(
        student_id=student.id
    ).all()

    applied_job_ids = [app.job_id for app in applications]

    # all approved & open jobs
    jobs = Job.query.filter_by(
        is_approved=True,
        is_closed=False
    ).all()

    return render_template(
        "student_dashboard.html",
        student=student,
        applications=applications,
        jobs=jobs,
        applied_job_ids=applied_job_ids
    )


@app.route("/student/apply/<int:job_id>")
def apply_job(job_id):

    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(session["user_id"])

    if user.role != "student":
        return redirect("/login")

    student = StudentProfile.query.filter_by(
        user_id=user.id
    ).first()

    # prevent duplicate application
    existing = Application.query.filter_by(
        job_id=job_id,
        student_id=student.id
    ).first()

    if existing:
        return redirect("/student/dashboard")

    application = Application(
        job_id=job_id,
        student_id=student.id,
        status="Applied"
    )

    db.session.add(application)
    db.session.commit()

    return redirect("/student/dashboard")



@app.route("/application/<int:app_id>/shortlist")
def shortlist_application(app_id):
    app = Application.query.get_or_404(app_id)
    app.status = "Shortlisted"
    db.session.commit()
    return redirect(request.referrer)


@app.route("/application/<int:app_id>/select")
def select_application(app_id):
    app = Application.query.get_or_404(app_id)
    app.status = "Selected"
    db.session.commit()
    return redirect(request.referrer)


@app.route("/application/<int:app_id>/reject")
def reject_application(app_id):
    app = Application.query.get_or_404(app_id)
    app.status = "Rejected"
    db.session.commit()
    return redirect(request.referrer)



@app.route("/company/job/<int:job_id>/applications")
def view_job_applications(job_id):

    if "user_id" not in session or session.get("role") != "company":
        return redirect("/login")

    job = Job.query.get_or_404(job_id)

    # security check: job must belong to logged-in company
    company = CompanyProfile.query.filter_by(
        user_id=session["user_id"]
    ).first()

    if job.company_id != company.id:
        return "Unauthorized access"

    applications = Application.query.filter_by(job_id=job.id).all()

    return render_template(
        "job_applications.html",
        job=job,
        applications=applications
    )

@app.route("/company/job/<int:job_id>/edit", methods=["GET", "POST"])
def edit_job(job_id):
    # make sure company is logged in
    if session.get("role") != "company":
        return redirect("/login")

    job = Job.query.get_or_404(job_id)

    # optional: extra safety check
    if job.company_id != session.get("user_id"):
        return "Unauthorized", 403

    if request.method == "POST":
        # update fields
        job.title = request.form["title"]
        job.skills = request.form["skills"]
        job.salary = request.form["salary"]
        job.description = request.form["description"]

        # once edited, send for approval again
        job.is_approved = False

        db.session.commit()
        return redirect("/company/dashboard")

    return render_template("edit_job.html", job=job)



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
            return redirect(("/company_wait"))



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

    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(session["user_id"])

    if not user or user.role != "company":
        return redirect("/login")

    company = CompanyProfile.query.filter_by(
        user_id=user.id
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

@app.route("/company/job/<int:job_id>/close")
def close_job(job_id):

    if "user_id" not in session or session.get("role") != "company":
        return redirect("/login")

    job = Job.query.get_or_404(job_id)

    company = CompanyProfile.query.filter_by(
        user_id=session["user_id"]
    ).first()

    if job.company_id != company.id:
        return "Unauthorized", 403

    job.is_closed = True
    db.session.commit()

    return redirect("/company/dashboard")


@app.route("/company/job/<int:job_id>/delete")
def delete_job(job_id):

    if "user_id" not in session or session.get("role") != "company":
        return redirect("/login")

    job = Job.query.get_or_404(job_id)

    company = CompanyProfile.query.filter_by(
        user_id=session["user_id"]
    ).first()

    # make sure company owns this job
    if job.company_id != company.id:
        return "Unauthorized", 403

    db.session.delete(job)
    db.session.commit()

    return redirect("/company/dashboard")


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