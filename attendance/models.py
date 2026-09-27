from django.db import models
from django.contrib.auth.models import User
import uuid


# =========================================================
# STUDENT
# =========================================================

class Student(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_profile"
    )

    name = models.CharField(
        max_length=100
    )

    roll_no = models.CharField(
        max_length=50,
        unique=True
    )

    course = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    year = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    # NEW
    branch = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    # NEW
    section = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    # NEW
    semester = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    email = models.EmailField(
        blank=True,
        null=True
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.name} ({self.roll_no})"


# =========================================================
# SUBJECT
# =========================================================

class Subject(models.Model):

    name = models.CharField(
        max_length=150
    )

    code = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    branch = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    semester = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        if self.code:
            return f"{self.code} - {self.name}"

        return self.name


# =========================================================
# ATTENDANCE SESSION
# =========================================================

class AttendanceSession(models.Model):

    session_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    # NEW - Subject for this QR session
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_sessions"
    )

    # NEW - Teacher who generated QR
    teacher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_sessions"
    )

    # NEW - Class information
    branch = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    section = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    semester = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    expires_at = models.DateTimeField()

    active = models.BooleanField(
        default=True
    )

    def __str__(self):

        if self.subject:
            return f"{self.subject.name} - {self.session_id}"

        return str(self.session_id)


# =========================================================
# ATTENDANCE
# =========================================================

class Attendance(models.Model):

    STATUS_CHOICES = [
        ("Present", "Present"),
        ("Absent", "Absent"),
    ]

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="attendances"
    )

    # Existing session UUID - kept so old records remain safe
    session_id = models.UUIDField(
        null=True,
        blank=True,
        editable=False
    )

    # NEW - Subject-wise attendance
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_records"
    )

    date = models.DateField(
        auto_now_add=True
    )

    time = models.TimeField(
        auto_now_add=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Absent"
    )

    latitude = models.FloatField(
        null=True,
        blank=True
    )

    longitude = models.FloatField(
        null=True,
        blank=True
    )

    location_verified = models.BooleanField(
        default=False
    )

    def __str__(self):

        subject_name = (
            self.subject.name
            if self.subject
            else "No Subject"
        )

        return (
            f"{self.student.name} - "
            f"{subject_name} - "
            f"{self.status} - "
            f"{self.date}"
        )