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