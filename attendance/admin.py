from django.contrib import admin
from .models import Student, AttendanceSession, Attendance


# ============================================================
# STUDENT ADMIN
# ============================================================

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "roll_no",
        "course",
        "year",
        "email",
        "phone",
    )

    search_fields = (
        "name",
        "roll_no",
        "course",
        "email",
        "phone",
    )

    list_filter = (
        "course",
        "year",
    )

    ordering = (
        "roll_no",
    )


# ============================================================
# ATTENDANCE SESSION ADMIN
# ============================================================

@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):

    list_display = (
        "session_id",
        "created_at",
        "expires_at",
        "active",
    )

    list_filter = (
        "active",
    )

    search_fields = (
        "session_id",
    )


# ============================================================
# ATTENDANCE ADMIN
# ============================================================

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):

    list_display = (
        "student",
        "date",
        "time",
        "status",
        "location_verified",
    )

    list_filter = (
        "status",
        "location_verified",
        "date",
    )

    search_fields = (
        "student__name",
        "student__roll_no",
    )

    ordering = (
        "-date",
        "-time",
    )