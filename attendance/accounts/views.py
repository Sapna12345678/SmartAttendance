from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from attendance.models import Student, Attendance


# =========================
# STUDENT LOGIN
# =========================
def student_login(request):

    if request.user.is_authenticated:
        return redirect("student_dashboard")

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            return redirect("student_dashboard")

        else:

            return render(
                request,
                "accounts/login.html",
                {
                    "error": "Invalid username or password."
                }
            )

    return render(
        request,
        "accounts/login.html"
    )


# =========================
# STUDENT DASHBOARD
# =========================
@login_required
def student_dashboard(request):

    try:
        student = request.user.student_profile

        attendances = Attendance.objects.filter(
            student=student
        ).order_by("-date", "-time")

        total_days = attendances.count()

        present_days = attendances.filter(
            status="Present"
        ).count()

        absent_days = attendances.filter(
            status="Absent"
        ).count()

        if total_days > 0:
            attendance_percentage = round(
                (present_days / total_days) * 100,
                1
            )
        else:
            attendance_percentage = 0

    except Student.DoesNotExist:

        student = None
        attendances = []
        total_days = 0
        present_days = 0
        absent_days = 0
        attendance_percentage = 0

    return render(
        request,
        "accounts/student_dashboard.html",
        {
            "student": student,
            "attendances": attendances,
            "total_days": total_days,
            "present_days": present_days,
            "absent_days": absent_days,
            "attendance_percentage": attendance_percentage,
        }
    )


# =========================
# STUDENT LOGOUT
# =========================
@login_required
def student_logout(request):

    logout(request)

    return redirect("student_login")
# =========================================================
# STUDENT REGISTRATION
# =========================================================

from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib import messages
from attendance.models import Student


def student_register(request):

    if request.user.is_authenticated:
        try:
            request.user.student_profile
            return redirect("student_dashboard")
        except Student.DoesNotExist:
            pass

    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        password2 = request.POST.get("password2", "")

        roll_no = request.POST.get("roll_no", "").strip()
        course = request.POST.get("course", "").strip()
        year = request.POST.get("year", "").strip()
        branch = request.POST.get("branch", "").strip()
        section = request.POST.get("section", "").strip()
        semester = request.POST.get("semester", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()

        if not name or not username or not password or not roll_no:
            messages.error(
                request,
                "Name, Username, Password and Roll Number are required."
            )
            return render(
                request,
                "accounts/student_register.html"
            )

        if password != password2:
            messages.error(
                request,
                "Passwords do not match."
            )
            return render(
                request,
                "accounts/student_register.html"
            )

        if User.objects.filter(username=username).exists():
            messages.error(
                request,
                "Username already exists. Please choose another username."
            )
            return render(
                request,
                "accounts/student_register.html"
            )

        if Student.objects.filter(roll_no=roll_no).exists():
            messages.error(
                request,
                "Roll number already exists."
            )
            return render(
                request,
                "accounts/student_register.html"
            )

        semester_value = None

        if semester:
            try:
                semester_value = int(semester)
            except ValueError:
                messages.error(
                    request,
                    "Semester must be a valid number."
                )
                return render(
                    request,
                    "accounts/student_register.html"
                )

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email
        )

        Student.objects.create(
            user=user,
            name=name,
            roll_no=roll_no,
            course=course,
            year=year,
            branch=branch,
            section=section,
            semester=semester_value,
            email=email,
            phone=phone
        )

        login(request, user)

        messages.success(
            request,
            "Registration successful! Welcome to Smart Attendance."
        )

        return redirect("student_dashboard")

    return render(
        request,
        "accounts/student_register.html"
    )