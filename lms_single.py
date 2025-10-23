import os
import jwt
import datetime
from flask import Flask, request, jsonify, redirect, render_template_string, make_response
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from django.conf import settings
import django

# ===============================
# DJANGO CONFIGURATION
# ===============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SECRET_KEY = "supersecretkey"

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY=SECRET_KEY,
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=["*"],
        INSTALLED_APPS=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.messages",
            "rest_framework",
        ],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": os.path.join(BASE_DIR, "lms.sqlite3"),
            }
        },
        TIME_ZONE="UTC",
        USE_TZ=True,
    )

django.setup()

# ===============================
# DJANGO MODELS
# ===============================
from django.db import models
from django.contrib.auth.models import User
from rest_framework import serializers, viewsets, routers
from django.urls import path, include

class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    instructor = models.CharField(max_length=100, default="Admin")
    class Meta:
        app_label = "lms_single"

class Enrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    class Meta:
        app_label = "lms_single"

# ===============================
# DJANGO REST API
# ===============================
class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = "__all__"

class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = "__all__"

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer

router = routers.DefaultRouter()
router.register(r"courses", CourseViewSet)
router.register(r"enrollments", EnrollmentViewSet)
urlpatterns = [path("api/", include(router.urls))]

# ===============================
# FLASK FRONTEND
# ===============================
app = Flask(__name__)

STYLE = """
<style>
body { font-family: 'Segoe UI', sans-serif; margin:0; background:#f8f9fb; color:#333; }
header { background:#004aad; color:white; padding:15px 30px; display:flex; justify-content:space-between; align-items:center; }
header a { color:white; margin:0 10px; text-decoration:none; font-weight:500; }
header a:hover { text-decoration:underline; }
.container { max-width:900px; margin:40px auto; background:white; padding:25px; border-radius:12px;
  box-shadow:0 0 15px rgba(0,0,0,0.1); }
button { background:#004aad; color:white; border:none; padding:10px 15px; border-radius:5px; cursor:pointer; }
input, textarea { width:100%; margin-bottom:10px; padding:8px; border:1px solid #ccc; border-radius:6px; }
.course-card { border:1px solid #e0e0e0; padding:15px; border-radius:8px; margin-bottom:10px; }
.course-card h3 { margin:0 0 8px; }
.alert { background:#eaf4ff; border-left:5px solid #004aad; padding:10px; margin-bottom:15px; }
footer { text-align:center; padding:20px; font-size:14px; color:#777; }
</style>
"""

def navbar(username=None):
    if username:
        links = f"""
        <a href="/">Home</a>
        <a href="/courses">Courses</a>
        <a href="/my-courses">My Courses</a>
        <a href="/admin">Admin</a>
        <a href="/logout">Logout ({username})</a>"""
    else:
        links = f"""
        <a href="/">Home</a>
        <a href="/login">Login</a>
        <a href="/register">Register</a>"""
    return f"<header><b>LMS Portal</b><nav>{links}</nav></header>"

# Utility
def get_user_from_cookie():
    token = request.cookies.get("token")
    if not token: return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return User.objects.get(id=payload["uid"])
    except Exception:
        return None

@app.route("/")
def home():
    user = get_user_from_cookie()
    html = f"""{STYLE}{navbar(user.username if user else None)}
    <div class='container'>
      <h2>Welcome to the LMS Portal</h2>
      <p>Browse, enroll, and manage your courses in one place.</p>
      <p>{'Logged in as <b>'+user.username+'</b>.' if user else 'Please log in or register to start learning.'}</p>
    </div><footer>© 2025 LMS Portal</footer>"""
    return html

@app.route("/register", methods=["GET", "POST"])
def register():
    from django.contrib.auth.models import User
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if User.objects.filter(username=username).exists():
            msg = "❌ Username already exists!"
        else:
            User.objects.create_user(username=username, password=password)
            msg = "✅ Registration successful! You can now log in."
    else:
        msg = ""
    return f"""{STYLE}{navbar()}
    <div class='container'>
      <h2>Register</h2>
      <form method='POST'>
        <input name='username' placeholder='Username' required>
        <input name='password' type='password' placeholder='Password' required>
        <button>Register</button>
      </form>
      <p class='alert'>{msg}</p>
    </div><footer>© 2025 LMS Portal</footer>"""

@app.route("/login", methods=["GET", "POST"])
def login():
    from django.contrib.auth.models import User
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                token = jwt.encode({"uid": user.id, "exp": datetime.datetime.utcnow()+datetime.timedelta(hours=4)},
                                   SECRET_KEY, algorithm="HS256")
                resp = make_response(redirect("/"))
                resp.set_cookie("token", token)
                return resp
            else:
                msg = "❌ Invalid password."
        except User.DoesNotExist:
            msg = "❌ User not found."
    else:
        msg = ""
    return f"""{STYLE}{navbar()}
    <div class='container'>
      <h2>Login</h2>
      <form method='POST'>
        <input name='username' placeholder='Username' required>
        <input name='password' type='password' placeholder='Password' required>
        <button>Login</button>
      </form>
      <p class='alert'>{msg}</p>
    </div><footer>© 2025 LMS Portal</footer>"""

@app.route("/logout")
def logout():
    resp = make_response(redirect("/"))
    resp.delete_cookie("token")
    return resp

@app.route("/courses")
def view_courses():
    user = get_user_from_cookie()
    if not user:
        return redirect("/login")
    courses = Course.objects.all()
    html = ""
    for c in courses:
        html += f"""
        <div class='course-card'>
          <h3>{c.title}</h3>
          <p>{c.description}</p>
          <p><i>Instructor: {c.instructor}</i></p>
          <form action='/enroll' method='post'>
            <input type='hidden' name='course_id' value='{c.id}'>
            <button>Enroll</button>
          </form>
        </div>"""
    return f"""{STYLE}{navbar(user.username)}
    <div class='container'><h2>Available Courses</h2>{html}</div><footer>© 2025 LMS Portal</footer>"""

@app.route("/my-courses")
def my_courses():
    user = get_user_from_cookie()
    if not user:
        return redirect("/login")
    enrollments = Enrollment.objects.filter(user=user)
    html = ""
    if not enrollments:
        html = "<p>You haven’t enrolled in any courses yet.</p>"
    else:
        for e in enrollments:
            html += f"<div class='course-card'><h3>{e.course.title}</h3><p>{e.course.description}</p></div>"
    return f"""{STYLE}{navbar(user.username)}
    <div class='container'><h2>My Courses</h2>{html}</div><footer>© 2025 LMS Portal</footer>"""

@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    user = get_user_from_cookie()
    if not user or not user.is_superuser:
        return redirect("/")
    msg = ""
    if request.method == "POST":
        title = request.form["title"]
        desc = request.form["description"]
        instr = request.form["instructor"]
        Course.objects.create(title=title, description=desc, instructor=instr)
        msg = "✅ Course added successfully!"
    return f"""{STYLE}{navbar(user.username)}
    <div class='container'>
      <h2>Admin Panel</h2>
      <form method='POST'>
        <input name='title' placeholder='Course Title' required>
        <textarea name='description' placeholder='Description' required></textarea>
        <input name='instructor' placeholder='Instructor' required>
        <button>Add Course</button>
      </form>
      <p class='alert'>{msg}</p>
    </div><footer>© 2025 LMS Portal</footer>"""

@app.route("/enroll", methods=["POST"])
def enroll():
    user = get_user_from_cookie()
    if not user:
        return redirect("/login")
    cid = request.form.get("course_id")
    course = Course.objects.get(id=cid)
    if not Enrollment.objects.filter(user=user, course=course).exists():
        Enrollment.objects.create(user=user, course=course)
        msg = f"✅ You have been enrolled in {course.title}!"
    else:
        msg = "ℹ️ You are already enrolled in this course."
    return f"<script>alert('{msg}');window.location='/my-courses';</script>"

# ===============================
# COMBINE DJANGO + FLASK
# ===============================
from django.core.wsgi import get_wsgi_application
django_app = get_wsgi_application()
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {"/api": django_app})

# ===============================
# AUTO MIGRATIONS
# ===============================
if __name__ == "__main__":
    from django.core.management import call_command
    print("🔄 Applying migrations...")
    call_command("migrate", interactive=False, run_syncdb=True, verbosity=0)
    print("✅ Migrations applied.")

    from django.contrib.auth.models import User
    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser("admin", "admin@example.com", "admin123")
        print("👑 Admin user created: admin / admin123")

    print("🚀 LMS running at http://127.0.0.1:5000")
    app.run(port=5000, debug=False)
