from django.urls import path
from . import views


urlpatterns = [

    # Student Login
    path(
        "login/",
        views.student_login,
        name="student_login"
    ),

    # Student Dashboard
    path(
        "dashboard/",
        views.student_dashboard,
        name="student_dashboard"
    ),

    # Student Logout
    path(
        "logout/",
        views.student_logout,
        name="student_logout"
    ),
]