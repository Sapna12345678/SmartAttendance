# =========================================================
# SMART ATTENDANCE - VIEWS.PY
# =========================================================

import os
import json
import math
import uuid

import qrcode

from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from openpyxl import Workbook

from .models import (
    Student,
    Subject,
    AttendanceSession,
    Attendance,
)


# =========================================================
# TEACHER AUTHENTICATION
# =========================================================

def teacher_required(view_func):

    def wrapper(request, *args, **kwargs):

        if not request.session.get("teacher_logged_in"):
            return redirect("teacher_login")

        return view_func(request, *args, **kwargs)

    return wrapper


# =========================================================
# HOME
# =========================================================

def home(request):

    return render(
        request,
        "attendance/home.html"
    )


# =========================================================
# TEACHER LOGIN
# =========================================================

def teacher_login(request):

    if request.session.get("teacher_logged_in"):
        return redirect("teacher_dashboard")

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(
                request,
                user
            )

            request.session[
                "teacher_logged_in"
            ] = True

            return redirect(
                "teacher_dashboard"
            )

        messages.error(
            request,
            "Invalid username or password."
        )

    return render(
        request,
        "attendance/teacher_login.html"
    )


# =========================================================
# TEACHER LOGOUT
# =========================================================

def teacher_logout(request):

    request.session.pop(
        "teacher_logged_in",
        None
    )

    logout(request)

    return redirect("home")


# =========================================================
# TEACHER DASHBOARD
# =========================================================

@teacher_required
def teacher_dashboard(request):

    today = timezone.localdate()

    total_students = Student.objects.count()

    total_attendance = Attendance.objects.count()

    present_today = Attendance.objects.filter(
        date=today,
        status="Present"
    ).count()

    absent_today = Attendance.objects.filter(
        date=today,
        status="Absent"
    ).count()

    total_today = (
        present_today +
        absent_today
    )

    attendance_percentage = (
        round(
            (present_today / total_today) * 100,
            1
        )
        if total_today > 0
        else 0
    )

    now = timezone.now()

    active_sessions = AttendanceSession.objects.filter(
        active=True,
        expires_at__gt=now
    ).select_related(
        "subject",
        "teacher"
    ).order_by(
        "-created_at"
    )

    recent_attendance = Attendance.objects.select_related(
        "student",
        "subject"
    ).order_by(
        "-date",
        "-time"
    )[:10]

    subjects = Subject.objects.filter(
        active=True
    ).order_by("name")

    students = Student.objects.all().order_by(
        "roll_no"
    )

    return render(
        request,
        "attendance/teacher_dashboard.html",
        {
            "total_students": total_students,
            "total_attendance": total_attendance,
            "present_today": present_today,
            "absent_today": absent_today,
            "attendance_percentage": attendance_percentage,
            "active_sessions": active_sessions,
            "active_qr_count": active_sessions.count(),
            "recent_attendance": recent_attendance,
            "subjects": subjects,
            "students": students,
            "today": today,
        }
    )


# =========================================================
# STUDENTS PAGE
# =========================================================

@teacher_required
def students_page(request):

    students = Student.objects.all().order_by(
        "roll_no"
    )

    return render(
        request,
        "attendance/students.html",
        {
            "students": students
        }
    )


# =========================================================
# CALCULATE GPS DISTANCE
# =========================================================

def calculate_distance(
    lat1,
    lon1,
    lat2,
    lon2
):

    try:

        lat1 = float(lat1)
        lon1 = float(lon1)
        lat2 = float(lat2)
        lon2 = float(lon2)

    except (
        TypeError,
        ValueError
    ):

        return None

    earth_radius = 6371000

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)

    delta_phi = math.radians(
        lat2 - lat1
    )

    delta_lambda = math.radians(
        lon2 - lon1
    )

    a = (
        math.sin(delta_phi / 2) ** 2
        +
        math.cos(phi1)
        *
        math.cos(phi2)
        *
        math.sin(delta_lambda / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return earth_radius * c


# =========================================================
# REQUEST DATA
# =========================================================

def get_request_data(request):

    if request.content_type == "application/json":

        try:

            body = request.body.decode("utf-8")

            if body:
                return json.loads(body)

        except (
            json.JSONDecodeError,
            UnicodeDecodeError
        ):

            return {}

        return {}

    return request.POST


# =========================================================
# GENERATE QR
# =========================================================

@teacher_required
def generate_qr(request):

    if request.method != "GET":

        return redirect(
            "generate_qr"
        )

    subjects = Subject.objects.filter(
        active=True
    ).order_by("name")

    subject_id = request.GET.get(
        "subject"
    )

    branch = request.GET.get(
        "branch",
        ""
    ).strip()

    section = request.GET.get(
        "section",
        ""
    ).strip()

    semester_raw = request.GET.get(
        "semester",
        ""
    ).strip()

    duration_raw = request.GET.get(
        "duration",
        "60"
    ).strip()

    if not subject_id:

        return render(
            request,
            "attendance/generate_qr.html",
            {
                "subjects": subjects,
            }
        )

    try:

        subject = subjects.get(
            id=subject_id
        )

    except Subject.DoesNotExist:

        return render(
            request,
            "attendance/generate_qr.html",
            {
                "subjects": subjects,
                "error": "Invalid subject selected.",
            }
        )

    try:

        duration = int(
            duration_raw
        )

    except (
        ValueError,
        TypeError
    ):

        duration = 60

    duration = max(
        30,
        min(duration, 300)
    )

    semester = None

    if semester_raw:

        try:

            semester = int(
                semester_raw
            )

        except (
            ValueError,
            TypeError
        ):

            semester = None

    if not branch:

        branch = subject.branch or ""

    if semester is None:

        semester = subject.semester

    AttendanceSession.objects.filter(
        active=True
    ).update(
        active=False
    )

    expires_at = (
        timezone.now()
        +
        timedelta(
            seconds=duration
        )
    )

    session = AttendanceSession.objects.create(
        subject=subject,
        teacher=request.user,
        branch=branch or None,
        section=section or None,
        semester=semester,
        expires_at=expires_at,
        active=True,
    )

    host = getattr(
        settings,
        "SMART_ATTENDANCE_HOST",
        "127.0.0.1:8000"
    )

    scan_url = (
        f"https://{host}/scan/"
        f"?session={session.session_id}"
    )

    qr_dir = os.path.join(
        settings.MEDIA_ROOT,
        "qr_codes"
    )

    os.makedirs(
        qr_dir,
        exist_ok=True
    )

    filename = (
        f"attendance_qr_"
        f"{session.session_id}.png"
    )

    qr_file_path = os.path.join(
        qr_dir,
        filename
    )

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )

    qr.add_data(
        scan_url
    )

    qr.make(
        fit=True
    )

    qr_image = qr.make_image()

    qr_image.save(
        qr_file_path
    )

    qr_image_url = (
        settings.MEDIA_URL
        +
        "qr_codes/"
        +
        filename
    )

    return render(
        request,
        "attendance/generate_qr.html",
        {
            "session": session,
            "subjects": subjects,
            "scan_url": scan_url,
            "qr_image_url": qr_image_url,
            "filename": filename,
            "selected_subject": str(
                subject.id
            ),
            "selected_branch": branch,
            "selected_section": section,
            "selected_semester": semester,
            "selected_duration": duration,
        }
    )


# =========================================================
# PROJECTOR
# =========================================================

@teacher_required
def projector(request):

    now = timezone.now()

    session = (
        AttendanceSession.objects
        .filter(
            active=True,
            expires_at__gt=now
        )
        .select_related(
            "subject"
        )
        .order_by(
            "-created_at"
        )
        .first()
    )

    scan_url = None

    if session:

        host = getattr(
            settings,
            "SMART_ATTENDANCE_HOST",
            "127.0.0.1:8000"
        )

        scan_url = (
            f"https://{host}/scan/"
            f"?session={session.session_id}"
        )

    return render(
        request,
        "attendance/projector.html",
        {
            "session": session,
            "scan_url": scan_url,
        }
    )


# =========================================================
# SCAN QR
# =========================================================

def scan_qr(request):

    session_id = request.GET.get(
        "session"
    )

    if not session_id:

        return render(
            request,
            "attendance/scan.html",
            {
                "error": "Invalid Attendance QR.",
            }
        )

    try:

        session_uuid = uuid.UUID(
            str(session_id)
        )

    except ValueError:

        return render(
            request,
            "attendance/scan.html",
            {
                "error": "Invalid Attendance QR.",
            }
        )

    try:

        session = (
            AttendanceSession.objects
            .select_related(
                "subject"
            )
            .get(
                session_id=session_uuid
            )
        )

    except AttendanceSession.DoesNotExist:

        return render(
            request,
            "attendance/scan.html",
            {
                "error": (
                    "Attendance session not found."
                ),
            }
        )

    if not session.active:

        return render(
            request,
            "attendance/scan.html",
            {
                "error": (
                    "This attendance QR is no longer active."
                ),
                "session": session,
            }
        )

    if timezone.now() >= session.expires_at:

        session.active = False

        session.save(
            update_fields=[
                "active"
            ]
        )

        return render(
            request,
            "attendance/scan.html",
            {
                "error": (
                    "QR expired. Please scan a fresh QR."
                ),
                "session": session,
            }
        )

    if not request.user.is_authenticated:

        login_url = (
            "/accounts/login/"
            f"?next=/scan/?session={session.session_id}"
        )

        return redirect(
            login_url
        )

    try:

        student = request.user.student_profile

    except Student.DoesNotExist:

        return render(
            request,
            "attendance/scan.html",
            {
                "session": session,
                "error": (
                    "Student profile not found."
                ),
            }
        )

    return render(
        request,
        "attendance/scan.html",
        {
            "session": session,
            "student": student,
            "error": None,
        }
    )


# =========================================================
# MARK ATTENDANCE
# =========================================================

@login_required
def mark_attendance(request):

    if request.method != "POST":

        return JsonResponse(
            {
                "success": False,
                "message": "POST request required."
            },
            status=405
        )

    data = get_request_data(
        request
    )

    session_id = data.get(
        "session_id"
    )

    latitude = data.get(
        "latitude"
    )

    longitude = data.get(
        "longitude"
    )

    accuracy = data.get(
        "accuracy"
    )

    if not session_id:

        return JsonResponse(
            {
                "success": False,
                "message": "Session ID is required."
            },
            status=400
        )

    try:

        session_uuid = uuid.UUID(
            str(session_id)
        )

    except ValueError:

        return JsonResponse(
            {
                "success": False,
                "message": "Invalid session ID."
            },
            status=400
        )

    try:

        session = (
            AttendanceSession.objects
            .select_related(
                "subject"
            )
            .get(
                session_id=session_uuid
            )
        )

    except AttendanceSession.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "Attendance session not found."
                )
            },
            status=404
        )

    if not session.active:

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "This QR session is inactive."
                )
            },
            status=400
        )

    if timezone.now() >= session.expires_at:

        session.active = False

        session.save(
            update_fields=[
                "active"
            ]
        )

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "QR expired. "
                    "Please scan a fresh QR."
                )
            },
            status=400
        )

    try:

        student = request.user.student_profile

    except Student.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "Student profile not found."
                )
            },
            status=400
        )

    if session.branch:

        if (
            not student.branch
            or
            student.branch.lower()
            != session.branch.lower()
        ):

            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Your branch does not "
                        "match this attendance session."
                    )
                },
                status=403
            )

    if session.section:

        if (
            not student.section
            or
            student.section.lower()
            != session.section.lower()
        ):

            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Your section does not "
                        "match this attendance session."
                    )
                },
                status=403
            )

    if session.semester is not None:

        if student.semester != session.semester:

            return JsonResponse(
                {
                    "success": False,
                    "message": (
                        "Your semester does not "
                        "match this attendance session."
                    )
                },
                status=403
            )

    already_marked = Attendance.objects.filter(
        student=student,
        session_id=session.session_id
    ).exists()

    if already_marked:

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "Attendance already marked "
                    "for this session."
                )
            },
            status=409
        )

    try:

        latitude = float(latitude)

        longitude = float(longitude)

    except (
        TypeError,
        ValueError
    ):

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "Unable to detect your location."
                )
            },
            status=400
        )

    try:

        accuracy_value = float(
            accuracy
        )

    except (
        TypeError,
        ValueError
    ):

        accuracy_value = None

    if (
        accuracy_value is not None
        and
        accuracy_value > 500
    ):

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "GPS accuracy is too low. "
                    "Please enable precise location "
                    "and try again."
                )
            },
            status=400
        )

    college_latitude = getattr(
        settings,
        "ATTENDANCE_LATITUDE",
        None
    )

    college_longitude = getattr(
        settings,
        "ATTENDANCE_LONGITUDE",
        None
    )

    allowed_radius = getattr(
        settings,
        "ATTENDANCE_RADIUS_METERS",
        300
    )

    if (
        college_latitude is None
        or
        college_longitude is None
    ):

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "College GPS location "
                    "is not configured."
                )
            },
            status=500
        )

    distance = calculate_distance(
        latitude,
        longitude,
        college_latitude,
        college_longitude
    )

    if distance is None:

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "Unable to calculate location."
                )
            },
            status=400
        )

    if distance > allowed_radius:

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "You are outside the college "
                    "attendance area."
                ),
                "distance": round(
                    distance,
                    2
                ),
                "allowed_radius": allowed_radius,
            },
            status=403
        )

    attendance = Attendance.objects.create(
        student=student,
        session_id=session.session_id,
        subject=session.subject,
        status="Present",
        latitude=latitude,
        longitude=longitude,
        location_verified=True,
    )

    return JsonResponse(
        {
            "success": True,
            "message": (
                "Attendance marked successfully."
            ),
            "attendance_id": attendance.id,
            "distance": round(
                distance,
                2
            ),
            "location_verified": True,
        }
    )


# =========================================================
# ATTENDANCE LIST / REPORT
# =========================================================

@teacher_required
def attendance_list(request):

    records = Attendance.objects.select_related(
        "student",
        "subject"
    ).order_by(
        "-date",
        "-time"
    )

    subject_id = request.GET.get(
        "subject",
        ""
    ).strip()

    student_id = request.GET.get(
        "student",
        ""
    ).strip()

    date_value = request.GET.get(
        "date",
        ""
    ).strip()

    status = request.GET.get(
        "status",
        ""
    ).strip()

    search = request.GET.get(
        "search",
        ""
    ).strip()

    # -----------------------------------------------------
    # SUBJECT FILTER
    # -----------------------------------------------------

    if subject_id:

        try:

            records = records.filter(
                subject_id=int(subject_id)
            )

        except (
            ValueError,
            TypeError
        ):

            pass

    # -----------------------------------------------------
    # STUDENT FILTER
    # -----------------------------------------------------

    if student_id:

        try:

            records = records.filter(
                student_id=int(student_id)
            )

        except (
            ValueError,
            TypeError
        ):

            pass

    # -----------------------------------------------------
    # DATE FILTER
    # -----------------------------------------------------

    if date_value:

        records = records.filter(
            date=date_value
        )

    # -----------------------------------------------------
    # STATUS FILTER
    # -----------------------------------------------------

    if status in [
        "Present",
        "Absent"
    ]:

        records = records.filter(
            status=status
        )

    # -----------------------------------------------------
    # SEARCH BY NAME / ROLL NUMBER
    # -----------------------------------------------------

    if search:

        records = records.filter(
            Q(
                student__name__icontains=search
            )
            |
            Q(
                student__roll_no__icontains=search
            )
        )

    # -----------------------------------------------------
    # REPORT STATISTICS
    # -----------------------------------------------------

    total_students = records.values(
        "student_id"
    ).distinct().count()

    present_count = records.filter(
        status="Present"
    ).count()

    absent_count = records.filter(
        status="Absent"
    ).count()

    total_records = (
        present_count +
        absent_count
    )

    attendance_percentage = (
        round(
            (present_count / total_records) * 100,
            1
        )
        if total_records > 0
        else 0
    )

    # -----------------------------------------------------
    # FILTER OPTIONS
    # -----------------------------------------------------

    subjects = Subject.objects.filter(
        active=True
    ).order_by(
        "name"
    )

    students = Student.objects.all().order_by(
        "roll_no"
    )

    # -----------------------------------------------------
    # REPORT TEMPLATE
    # -----------------------------------------------------

    return render(
        request,
        "attendance/attendance_list.html",
        {
            "attendances": records,
            "records": records,

            "subjects": subjects,
            "students": students,

            "selected_subject": subject_id,
            "selected_student": student_id,
            "selected_date": date_value,
            "selected_status": status,

            "search": search,

            "total_students": total_students,
            "present_count": present_count,
            "absent_count": absent_count,
            "attendance_percentage": attendance_percentage,
        }
    )


# =========================================================
# TODAY ATTENDANCE
# =========================================================

@teacher_required
def today_attendance(request):

    today = timezone.localdate()

    records = Attendance.objects.select_related(
        "student",
        "subject"
    ).filter(
        date=today
    ).order_by(
        "-time"
    )

    present_count = records.filter(
        status="Present"
    ).count()

    absent_count = records.filter(
        status="Absent"
    ).count()

    total_students = records.values(
        "student_id"
    ).distinct().count()

    total_records = (
        present_count +
        absent_count
    )

    attendance_percentage = (
        round(
            (present_count / total_records) * 100,
            1
        )
        if total_records > 0
        else 0
    )

    return render(
        request,
        "attendance/attendance_list.html",
        {
            "attendances": records,
            "records": records,

            "present_count": present_count,
            "absent_count": absent_count,

            "total_students": total_students,
            "attendance_percentage": attendance_percentage,

            "selected_date": str(today),
            "today": today,

            "subjects": Subject.objects.filter(
                active=True
            ).order_by("name"),

            "students": Student.objects.all().order_by(
                "roll_no"
            ),

            "selected_subject": "",
            "selected_student": "",
            "selected_status": "",
            "search": "",
        }
    )


# =========================================================
# SUBJECT-WISE ATTENDANCE
# =========================================================

@teacher_required
def subject_wise_attendance(request):

    subjects = Subject.objects.filter(
        active=True
    ).order_by("name")

    selected_subject_id = request.GET.get(
        "subject"
    )

    subject = None

    records = Attendance.objects.none()

    student_summary = []

    if selected_subject_id:

        try:

            subject = subjects.get(
                id=selected_subject_id
            )

        except Subject.DoesNotExist:

            subject = None

    if subject:

        records = Attendance.objects.select_related(
            "student",
            "subject"
        ).filter(
            subject=subject
        ).order_by(
            "student__roll_no",
            "-date",
            "-time"
        )

        students = Student.objects.all().order_by(
            "roll_no"
        )

        for student in students:

            student_records = records.filter(
                student=student
            )

            total = student_records.count()

            present = student_records.filter(
                status="Present"
            ).count()

            absent = student_records.filter(
                status="Absent"
            ).count()

            percentage = (
                round(
                    (present / total) * 100,
                    1
                )
                if total > 0
                else 0
            )

            student_summary.append(
                {
                    "student": student,
                    "total": total,
                    "present": present,
                    "absent": absent,
                    "percentage": percentage,
                }
            )

    return render(
        request,
        "attendance/subject_wise.html",
        {
            "subjects": subjects,
            "selected_subject": subject,
            "subject": subject,
            "records": records,
            "student_summary": student_summary,
        }
    )


# =========================================================
# STUDENT HISTORY
# =========================================================

@teacher_required
def student_history(request):

    students = Student.objects.all().order_by(
        "roll_no"
    )

    selected_student_id = request.GET.get(
        "student"
    )

    student = None

    records = Attendance.objects.none()

    total = 0
    present = 0
    absent = 0
    percentage = 0

    if selected_student_id:

        try:

            student = Student.objects.get(
                id=selected_student_id
            )

            records = Attendance.objects.select_related(
                "subject"
            ).filter(
                student=student
            ).order_by(
                "-date",
                "-time"
            )

            total = records.count()

            present = records.filter(
                status="Present"
            ).count()

            absent = records.filter(
                status="Absent"
            ).count()

            percentage = (
                round(
                    (present / total) * 100,
                    1
                )
                if total > 0
                else 0
            )

        except Student.DoesNotExist:

            student = None

    return render(
        request,
        "attendance/student_history.html",
        {
            "students": students,
            "student": student,
            "records": records,
            "attendances": records,
            "total": total,
            "present": present,
            "absent": absent,
            "percentage": percentage,
        }
    )


# =========================================================
# EXCEL EXPORT
# =========================================================

@teacher_required
def export_attendance_excel(request):

    records = Attendance.objects.select_related(
        "student",
        "subject"
    ).order_by(
        "-date",
        "-time"
    )

    subject_id = request.GET.get(
        "subject",
        ""
    ).strip()

    student_id = request.GET.get(
        "student",
        ""
    ).strip()

    date_value = request.GET.get(
        "date",
        ""
    ).strip()

    status = request.GET.get(
        "status",
        ""
    ).strip()

    search = request.GET.get(
        "search",
        ""
    ).strip()

    # -----------------------------------------------------
    # SUBJECT FILTER
    # -----------------------------------------------------

    if subject_id:

        try:

            records = records.filter(
                subject_id=int(subject_id)
            )

        except (
            ValueError,
            TypeError
        ):

            pass

    # -----------------------------------------------------
    # STUDENT FILTER
    # -----------------------------------------------------

    if student_id:

        try:

            records = records.filter(
                student_id=int(student_id)
            )

        except (
            ValueError,
            TypeError
        ):

            pass

    # -----------------------------------------------------
    # DATE FILTER
    # -----------------------------------------------------

    if date_value:

        records = records.filter(
            date=date_value
        )

    # -----------------------------------------------------
    # STATUS FILTER
    # -----------------------------------------------------

    if status in [
        "Present",
        "Absent"
    ]:

        records = records.filter(
            status=status
        )

    # -----------------------------------------------------
    # SEARCH BY NAME / ROLL NUMBER
    # -----------------------------------------------------

    if search:

        records = records.filter(
            Q(
                student__name__icontains=search
            )
            |
            Q(
                student__roll_no__icontains=search
            )
        )

    # -----------------------------------------------------
    # CREATE EXCEL
    # -----------------------------------------------------

    workbook = Workbook()

    worksheet = workbook.active

    worksheet.title = "Attendance"

    headers = [
        "ID",
        "Student Name",
        "Roll No",
        "Branch",
        "Section",
        "Semester",
        "Subject",
        "Subject Code",
        "Date",
        "Time",
        "Status",
        "Latitude",
        "Longitude",
        "Location Verified",
        "Session ID",
    ]

    worksheet.append(
        headers
    )

    for record in records:

        worksheet.append(
            [
                record.id,
                record.student.name,
                record.student.roll_no,
                record.student.branch or "",
                record.student.section or "",
                record.student.semester or "",
                (
                    record.subject.name
                    if record.subject
                    else "General"
                ),
                (
                    record.subject.code
                    if (
                        record.subject
                        and
                        record.subject.code
                    )
                    else ""
                ),
                record.date,
                record.time,
                record.status,
                (
                    record.latitude
                    if record.latitude is not None
                    else ""
                ),
                (
                    record.longitude
                    if record.longitude is not None
                    else ""
                ),
                (
                    "Yes"
                    if record.location_verified
                    else "No"
                ),
                (
                    str(record.session_id)
                    if record.session_id
                    else ""
                ),
            ]
        )

    # -----------------------------------------------------
    # COLUMN WIDTH
    # -----------------------------------------------------

    for column in worksheet.columns:

        max_length = 0

        column_letter = (
            column[0].column_letter
        )

        for cell in column:

            try:

                value_length = len(
                    str(cell.value)
                )

                max_length = max(
                    max_length,
                    value_length
                )

            except Exception:

                pass

        worksheet.column_dimensions[
            column_letter
        ].width = min(
            max_length + 2,
            40
        )

    response = HttpResponse(
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )

    filename = (
        f"attendance_report_"
        f"{timezone.localdate()}.xlsx"
    )

    response[
        "Content-Disposition"
    ] = (
        f'attachment; filename="{filename}"'
    )

    workbook.save(
        response
    )

    return response


# =========================================================
# MARK ABSENT STUDENTS
# =========================================================

@teacher_required
def mark_absent_students(request):

    if request.method != "POST":

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "POST request required."
                )
            },
            status=405
        )

    session_id = request.POST.get(
        "session_id"
    )

    if not session_id:

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "Session ID is required."
                )
            },
            status=400
        )

    try:

        session_uuid = uuid.UUID(
            str(session_id)
        )

    except ValueError:

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "Invalid session ID."
                )
            },
            status=400
        )

    try:

        session = (
            AttendanceSession.objects
            .select_related(
                "subject"
            )
            .get(
                session_id=session_uuid
            )
        )

    except AttendanceSession.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "Attendance session not found."
                )
            },
            status=404
        )

    # -----------------------------------------------------
    # ELIGIBLE STUDENTS
    # -----------------------------------------------------

    students = Student.objects.all()

    if session.semester is not None:

        students = students.filter(
            semester=session.semester
        )

    if session.branch:

        students = students.filter(
            branch__iexact=session.branch
        )

    if session.section:

        students = students.filter(
            section__iexact=session.section
        )

    marked_count = 0

    for student in students:

        exists = Attendance.objects.filter(
            student=student,
            session_id=session.session_id
        ).exists()

        if not exists:

            Attendance.objects.create(
                student=student,
                session_id=session.session_id,
                subject=session.subject,
                status="Absent",
                location_verified=False,
            )

            marked_count += 1

    session.active = False

    session.save(
        update_fields=[
            "active"
        ]
    )

    return JsonResponse(
        {
            "success": True,
            "message": (
                f"{marked_count} absent "
                "students marked successfully."
            ),
            "marked_count": marked_count,
        }
    )


# =========================================================
# CLEAN EXPIRED SESSIONS
# =========================================================

@teacher_required
def clean_expired_sessions(request):

    now = timezone.now()

    updated = (
        AttendanceSession.objects
        .filter(
            active=True,
            expires_at__lte=now
        )
        .update(
            active=False
        )
    )

    return JsonResponse(
        {
            "success": True,
            "cleaned_sessions": updated,
        }
    )