from django.contrib import admin
from .models import Student, Subject, AttendanceSession, Attendance


# ============================================================
# STUDENT ADMIN
# ============================================================

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):

    # -------------------------
    # STUDENT LIST PAGE
    # -------------------------
    list_display = (
        "name",
        "roll_no",
        "course",
        "year",
        "branch",
        "section",
        "semester",
        "email",
        "phone",
    )

    search_fields = (
        "name",
        "roll_no",
        "course",
        "branch",
        "section",
        "email",
        "phone",
    )

    list_filter = (
        "course",
        "year",
        "branch",
        "section",
        "semester",
    )

    ordering = (
        "roll_no",
    )

    # -------------------------
    # ADD / EDIT STUDENT FORM
    # -------------------------
    fieldsets = (

        (
            "👤 Account Information",
            {
                "fields": (
                    "user",
                    "name",
                    "email",
                    "phone",
                ),
                "description": (
                    "Link the student with a login account and "
                    "enter the student's basic contact information."
                ),
            },
        ),

        (
            "🎓 Academic Information",
            {
                "fields": (
                    "roll_no",
                    "course",
                    "year",
                    "branch",
                    "section",
                    "semester",
                ),
                "description": (
                    "Enter the student's academic and class details."
                ),
            },
        ),

    )


# ============================================================
# SUBJECT ADMIN
# ============================================================

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):

    list_display = (
        "code",
        "name",
        "branch",
        "semester",
        "active",
        "created_at",
    )

    search_fields = (
        "name",
        "code",
        "branch",
    )

    list_filter = (
        "branch",
        "semester",
        "active",
    )

    ordering = (
        "code",
        "name",
    )


# ============================================================
# ATTENDANCE SESSION ADMIN
# ============================================================

@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):

    list_display = (
        "session_id",
        "subject",
        "teacher",
        "branch",
        "section",
        "semester",
        "created_at",
        "expires_at",
        "active",
    )

    list_filter = (
        "active",
        "branch",
        "section",
        "semester",
        "subject",
    )

    search_fields = (
        "session_id",
        "subject__name",
        "subject__code",
        "teacher__username",
    )

    ordering = (
        "-created_at",
    )


# ============================================================
# ATTENDANCE ADMIN
# ============================================================

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):

    list_display = (
        "student",
        "subject",
        "date",
        "time",
        "status",
        "location_verified",
    )

    list_filter = (
        "status",
        "location_verified",
        "subject",
        "date",
    )

    search_fields = (
        "student__name",
        "student__roll_no",
        "subject__name",
        "subject__code",
    )

    ordering = (
        "-date",
        "-time",
    )