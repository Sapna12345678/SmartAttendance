from django.urls import path
from . import views


urlpatterns = [

    # =====================================================
    # HOME
    # =====================================================

    path(
        "",
        views.home,
        name="home"
    ),

    # =====================================================
    # TEACHER
    # =====================================================

    path(
        "teacher-login/",
        views.teacher_login,
        name="teacher_login"
    ),

    path(
        "teacher-dashboard/",
        views.teacher_dashboard,
        name="teacher_dashboard"
    ),

    path(
        "teacher-logout/",
        views.teacher_logout,
        name="teacher_logout"
    ),

    # =====================================================
    # STUDENTS
    # =====================================================

    path(
        "students/",
        views.students_page,
        name="students_page"
    ),

    # =====================================================
    # QR ATTENDANCE
    # =====================================================

    path(
        "generate-qr/",
        views.generate_qr,
        name="generate_qr"
    ),

    path(
        "projector/",
        views.projector,
        name="projector"
    ),

    path(
        "scan/",
        views.scan_qr,
        name="scan_qr"
    ),

    path(
        "mark-attendance/",
        views.mark_attendance,
        name="mark_attendance"
    ),

    # =====================================================
    # ATTENDANCE
    # =====================================================

    path(
        "attendance-list/",
        views.attendance_list,
        name="attendance_list"
    ),

    path(
        "today-attendance/",
        views.today_attendance,
        name="today_attendance"
    ),

    path(
        "subject-wise/",
        views.subject_wise_attendance,
        name="subject_wise_attendance"
    ),

    path(
        "student-history/",
        views.student_history,
        name="student_history"
    ),

    # =====================================================
    # REPORTS
    # =====================================================

    path(
        "export-attendance/",
        views.export_attendance_excel,
        name="export_attendance_excel"
    ),

    path(
        "mark-absent/",
        views.mark_absent_students,
        name="mark_absent_students"
    ),

    path(
        "clean-expired-sessions/",
        views.clean_expired_sessions,
        name="clean_expired_sessions"
    ),
]