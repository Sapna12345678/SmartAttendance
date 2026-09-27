# =========================================================
# SMART ATTENDANCE - VIEWS.PY
# =========================================================

import os
import base64
import json
import math
import uuid
from io import BytesIO
from datetime import timedelta

import qrcode

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
# TEACHER LOGIN CHECK
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

    if request.method == "POST":

        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            request.session["teacher_logged_in"] = True

            login(
                request,
                user
            )

            return redirect("teacher_dashboard")

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

    # -----------------------------------------------------
    # BASIC COUNTS
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # ATTENDANCE PERCENTAGE
    # -----------------------------------------------------

    if total_attendance > 0:

        attendance_percentage = round(
            (
                Attendance.objects.filter(
                    status="Present"
                ).count()
                / total_attendance
            ) * 100,
            2
        )

    else:

        attendance_percentage = 0

    # -----------------------------------------------------
    # ACTIVE QR SESSIONS
    #
    # IMPORTANT:
    # Do NOT use .count() here because the dashboard
    # template loops through active_sessions.
    # -----------------------------------------------------

    active_sessions = AttendanceSession.objects.filter(
        active=True,
        expires_at__gt=timezone.now()
    ).select_related(
        "subject",
        "teacher"
    ).order_by(
        "-created_at"
    )

    active_qr_count = active_sessions.count()

    # -----------------------------------------------------
    # RECENT ATTENDANCE
    # -----------------------------------------------------

    recent_attendance = Attendance.objects.select_related(
        "student",
        "subject"
    ).order_by(
        "-date",
        "-time"
    )[:10]

    # -----------------------------------------------------
    # ACTIVE SUBJECTS
    # -----------------------------------------------------

    active_subjects = Subject.objects.filter(
        active=True
    ).order_by(
        "code"
    )

    # -----------------------------------------------------
    # STUDENTS
    # -----------------------------------------------------

    students = Student.objects.all().order_by(
        "roll_no"
    )

    # -----------------------------------------------------
    # CONTEXT
    # -----------------------------------------------------

    context = {

        "total_students": total_students,

        "total_attendance": total_attendance,

        "present_today": present_today,

        "absent_today": absent_today,

        "attendance_percentage": attendance_percentage,

        "active_sessions": active_sessions,

        "active_qr_count": active_qr_count,

        "recent_attendance": recent_attendance,

        "active_subjects": active_subjects,

        "students": students,

    }

    return render(
        request,
        "attendance/teacher_dashboard.html",
        context
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
# GET PUBLIC HOST
# =========================================================

def get_public_host():

    cloudflare_file = os.path.join(
        settings.BASE_DIR,
        "cloudflare_url.txt"
    )

    if os.path.exists(cloudflare_file):

        try:

            with open(
                cloudflare_file,
                "r",
                encoding="utf-8"
            ) as f:

                host = f.read().strip()

            host = host.replace(
                "https://",
                ""
            ).replace(
                "http://",
                ""
            ).rstrip("/")

            if host:

                return host

        except Exception:

            pass

    return getattr(
        settings,
        "SMART_ATTENDANCE_HOST",
        "127.0.0.1:8000"
    ).replace(
        "https://",
        ""
    ).replace(
        "http://",
        ""
    ).rstrip("/")


# =========================================================
# CALCULATE DISTANCE
# =========================================================

def calculate_distance(
    lat1,
    lon1,
    lat2,
    lon2
):

    radius = 6371000

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

    return radius * c


# =========================================================
# GET REQUEST DATA
# =========================================================

def get_request_data(request):

    if request.content_type == "application/json":

        try:

            return json.loads(
                request.body.decode("utf-8")
            )

        except Exception:

            return {}

    return request.POST


# =========================================================
# GENERATE QR
# =========================================================

@teacher_required
def generate_qr(request):

    selected_subject = request.GET.get('subject', '').strip()
    selected_branch = request.GET.get('branch', '').strip()
    selected_section = request.GET.get('section', '').strip()
    selected_semester = request.GET.get('semester', '').strip()
    duration_raw = request.GET.get('duration', '60').strip()

    try:
        duration = int(duration_raw)
    except (ValueError, TypeError):
        duration = 60

    duration = max(30, min(duration, 300))

    try:
        if 'Semester' in selected_semester:
            selected_semester = int(selected_semester.split()[-1])
        elif selected_semester:
            selected_semester = int(selected_semester)
    except (ValueError, TypeError):
        selected_semester = 3

    subjects = Subject.objects.filter(active=True).order_by('code')
    subject_obj = None

    if selected_subject:
        try:
            subject_obj = Subject.objects.get(
                id=int(selected_subject),
                active=True
            )
        except (ValueError, TypeError, Subject.DoesNotExist):
            try:
                subject_obj = Subject.objects.get(
                    code=selected_subject,
                    active=True
                )
            except Subject.DoesNotExist:
                subject_obj = None

    if subject_obj:
        if not selected_branch:
            selected_branch = subject_obj.branch or ''
        if not selected_semester:
            selected_semester = subject_obj.semester or 3

    if not selected_branch:
        selected_branch = 'mca'

    if not selected_section:
        selected_section = 'b'

    if not selected_semester:
        selected_semester = 3

    try:
        selected_semester = int(selected_semester)
    except (ValueError, TypeError):
        selected_semester = 3

    AttendanceSession.objects.filter(active=True).update(active=False)

    now = timezone.now()
    expires_at = now + timedelta(seconds=duration)

    session = AttendanceSession.objects.create(
        subject=subject_obj,
        teacher=(request.user if request.user.is_authenticated else None),
        branch=selected_branch,
        section=selected_section,
        semester=selected_semester,
        created_at=now,
        expires_at=expires_at,
        active=True,
    )

    host = get_public_host()

    scan_url = (
        f'https://{host}/scan/'
        f'?session={session.session_id}'
    )

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )

    qr.add_data(scan_url)
    qr.make(fit=True)
    qr_image = qr.make_image()

    qr_directory = os.path.join(
        settings.MEDIA_ROOT,
        'qr_codes'
    )

    os.makedirs(qr_directory, exist_ok=True)

    filename = f'attendance_qr_{session.session_id}.png'
    qr_file_path = os.path.join(qr_directory, filename)
    qr_image.save(qr_file_path)

    buffer = BytesIO()
    qr_image.save(buffer, format='PNG')

    qr_image_base64 = (
        'data:image/png;base64,'
        + base64.b64encode(buffer.getvalue()).decode('utf-8')
    )

    context = {
        'subjects': subjects,
        'session': session,
        'scan_url': scan_url,
        'qr_image_base64': qr_image_base64,
        'duration': duration,
        'selected_subject': selected_subject,
        'selected_branch': selected_branch,
        'selected_section': selected_section,
        'selected_semester': selected_semester,
    }

    return render(
        request,
        'attendance/generate_qr.html',
        context
    )


# =========================================================
# PROJECTOR
# =========================================================

@teacher_required
def projector(request):

    session_id = request.GET.get(
        "session",
        ""
    ).strip()

    session = None

    if session_id:

        try:

            session = AttendanceSession.objects.select_related(
                "subject"
            ).get(
                session_id=uuid.UUID(session_id)
            )

        except (
            ValueError,
            AttendanceSession.DoesNotExist
        ):

            session = None

    return render(
        request,
        "attendance/projector.html",
        {
            "session": session
        }
    )


# =========================================================
# SCAN QR
# =========================================================

def scan_qr(request):

    session_id = request.GET.get(
        "session",
        ""
    ).strip()

    if not session_id:

        return JsonResponse(
            {
                "valid": False,
                "error": "Session ID is missing."
            },
            status=400
        )

    try:

        session_uuid = uuid.UUID(
            session_id
        )

    except ValueError:

        return JsonResponse(
            {
                "valid": False,
                "error": "Invalid session ID."
            },
            status=400
        )

    try:

        session = AttendanceSession.objects.select_related(
            "subject"
        ).get(
            session_id=session_uuid
        )

    except AttendanceSession.DoesNotExist:

        return JsonResponse(
            {
                "valid": False,
                "error": "Attendance session not found."
            },
            status=404
        )

    now = timezone.now()

    if not session.active:

        return JsonResponse(
            {
                "valid": False,
                "error": "Attendance session is no longer active."
            },
            status=400
        )

    if session.expires_at <= now:

        session.active = False

        session.save(
            update_fields=["active"]
        )

        return JsonResponse(
            {
                "valid": False,
                "error": "Attendance QR has expired."
            },
            status=400
        )

    # -----------------------------------------------------
    # JSON CHECK
    # -----------------------------------------------------

    if request.GET.get("data") == "1":

        remaining = int(
            max(
                0,
                (
                    session.expires_at - now
                ).total_seconds()
            )
        )

        return JsonResponse(
            {
                "valid": True,

                "session_id": str(
                    session.session_id
                ),

                "subject": (
                    str(session.subject)
                    if session.subject
                    else ""
                ),

                "branch": session.branch,

                "section": session.section,

                "semester": session.semester,

                "expires_at": session.expires_at.isoformat(),

                "remaining_seconds": remaining,

            }
        )

    # -----------------------------------------------------
    # STUDENT LOGIN
    # -----------------------------------------------------

    if not request.user.is_authenticated:

        return redirect(
            "/accounts/login/?next="
            + request.get_full_path()
        )

    # -----------------------------------------------------
    # STUDENT PROFILE
    # -----------------------------------------------------

    try:

        student = request.user.student_profile

    except Student.DoesNotExist:

        return render(
            request,
            "attendance/scan.html",
            {
                "session": session,

                "error": (
                    "Student profile is not connected "
                    "with this account."
                )
            }
        )

    return render(
        request,
        "attendance/scan.html",
        {
            "session": session,

            "student": student
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
                "error": "Only POST method is allowed."
            },
            status=405
        )

    data = get_request_data(
        request
    )

    session_id = str(
        data.get(
            "session",
            data.get(
                "session_id",
                ""
            )
        )
    ).strip()

    if not session_id:

        return JsonResponse(
            {
                "success": False,
                "error": "Session ID is required."
            },
            status=400
        )

    try:

        session_uuid = uuid.UUID(
            session_id
        )

    except ValueError:

        return JsonResponse(
            {
                "success": False,
                "error": "Invalid session ID."
            },
            status=400
        )

    try:

        session = AttendanceSession.objects.select_related(
            "subject"
        ).get(
            session_id=session_uuid
        )

    except AttendanceSession.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "error": "Attendance session not found."
            },
            status=404
        )

    # -----------------------------------------------------
    # SESSION VALIDATION
    # -----------------------------------------------------

    now = timezone.now()

    if not session.active:

        return JsonResponse(
            {
                "success": False,
                "error": "Attendance session is inactive."
            },
            status=400
        )

    if session.expires_at <= now:

        session.active = False

        session.save(
            update_fields=["active"]
        )

        return JsonResponse(
            {
                "success": False,
                "error": "Attendance QR has expired."
            },
            status=400
        )

    # -----------------------------------------------------
    # STUDENT PROFILE
    # -----------------------------------------------------

    try:

        student = request.user.student_profile

    except Student.DoesNotExist:

        return JsonResponse(
            {
                "success": False,
                "error": "Student profile not found."
            },
            status=400
        )

    # -----------------------------------------------------
    # BRANCH CHECK
    # -----------------------------------------------------

    if (
        session.branch
        and student.branch
        and session.branch.lower()
        != student.branch.lower()
    ):

        Attendance.objects.create(

            student=student,

            session_id=session.session_id,

            subject=session.subject,

            date=timezone.localdate(),

            time=timezone.localtime().time(),

            status="Absent",

            location_verified=False,

        )

        return JsonResponse(
            {
                "success": False,

                "status": "Absent",

                "error": "Branch does not match."
            },
            status=403
        )

    # -----------------------------------------------------
    # SECTION CHECK
    # -----------------------------------------------------

    if (
        session.section
        and student.section
        and session.section.lower()
        != student.section.lower()
    ):

        Attendance.objects.create(

            student=student,

            session_id=session.session_id,

            subject=session.subject,

            date=timezone.localdate(),

            time=timezone.localtime().time(),

            status="Absent",

            location_verified=False,

        )

        return JsonResponse(
            {
                "success": False,

                "status": "Absent",

                "error": "Section does not match."
            },
            status=403
        )

    # -----------------------------------------------------
    # SEMESTER CHECK
    # -----------------------------------------------------

    if (
        session.semester
        and student.semester
        and session.semester.lower()
        != student.semester.lower()
    ):

        Attendance.objects.create(

            student=student,

            session_id=session.session_id,

            subject=session.subject,

            date=timezone.localdate(),

            time=timezone.localtime().time(),

            status="Absent",

            location_verified=False,

        )

        return JsonResponse(
            {
                "success": False,

                "status": "Absent",

                "error": "Semester does not match."
            },
            status=403
        )

    # -----------------------------------------------------
    # DUPLICATE CHECK
    # -----------------------------------------------------

    already_marked = Attendance.objects.filter(
        student=student,
        session_id=session.session_id
    ).exists()

    if already_marked:

        return JsonResponse(
            {
                "success": False,

                "error": "Attendance already marked."
            },
            status=400
        )

    # -----------------------------------------------------
    # GPS DATA
    # -----------------------------------------------------

    latitude_raw = data.get(
        "latitude",
        data.get(
            "lat",
            ""
        )
    )

    longitude_raw = data.get(
        "longitude",
        data.get(
            "lon",
            data.get(
                "lng",
                ""
            )
        )
    )

    accuracy_raw = data.get(
        "accuracy",
        ""
    )

    try:

        latitude = float(
            latitude_raw
        )

        longitude = float(
            longitude_raw
        )

    except (
        TypeError,
        ValueError
    ):

        return JsonResponse(
            {
                "success": False,

                "error": (
                    "Location could not be detected. "
                    "Please allow GPS permission."
                )
            },
            status=400
        )

    accuracy = None

    if accuracy_raw not in (
        "",
        None
    ):

        try:

            accuracy = float(
                accuracy_raw
            )

        except (
            TypeError,
            ValueError
        ):

            accuracy = None

    # -----------------------------------------------------
    # GPS ACCURACY
    # -----------------------------------------------------

    if accuracy is not None and accuracy > 500:

        return JsonResponse(
            {
                "success": False,

                "error": (
                    "GPS accuracy is too low. "
                    "Please move to an open area "
                    "and try again."
                )
            },
            status=400
        )

    # -----------------------------------------------------
    # COLLEGE LOCATION
    # -----------------------------------------------------

    college_latitude = float(
        getattr(
            settings,
            "ATTENDANCE_LATITUDE",
            25.342787
        )
    )

    college_longitude = float(
        getattr(
            settings,
            "ATTENDANCE_LONGITUDE",
            81.902116
        )
    )

    allowed_radius = float(
        getattr(
            settings,
            "ATTENDANCE_RADIUS_METERS",
            300
        )
    )

    # -----------------------------------------------------
    # DISTANCE
    # -----------------------------------------------------

    distance = calculate_distance(

        latitude,

        longitude,

        college_latitude,

        college_longitude

    )

    # -----------------------------------------------------
    # OUTSIDE COLLEGE
    # -----------------------------------------------------

    if distance > allowed_radius:

        Attendance.objects.create(

            student=student,

            session_id=session.session_id,

            subject=session.subject,

            date=timezone.localdate(),

            time=timezone.localtime().time(),

            status="Absent",

            latitude=latitude,

            longitude=longitude,

            location_verified=False,

        )

        return JsonResponse(
            {
                "success": False,

                "status": "Absent",

                "error": (
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

    # -----------------------------------------------------
    # PRESENT
    # -----------------------------------------------------

    attendance = Attendance.objects.create(

        student=student,

        session_id=session.session_id,

        subject=session.subject,

        date=timezone.localdate(),

        time=timezone.localtime().time(),

        status="Present",

        latitude=latitude,

        longitude=longitude,

        location_verified=True,

    )

    return JsonResponse(
        {
            "success": True,

            "status": "Present",

            "message": (
                "Attendance marked successfully."
            ),

            "attendance_id": attendance.id,

            "distance": round(
                distance,
                2
            ),

        }
    )


# =========================================================
# ATTENDANCE LIST
# =========================================================

@teacher_required
def attendance_list(request):

    attendance_records = Attendance.objects.select_related(
        "student",
        "subject"
    ).order_by(
        "-date",
        "-time"
    )

    date_filter = request.GET.get(
        "date",
        ""
    ).strip()

    subject_filter = request.GET.get(
        "subject",
        ""
    ).strip()

    status_filter = request.GET.get(
        "status",
        ""
    ).strip()

    if date_filter:

        attendance_records = attendance_records.filter(
            date=date_filter
        )

    if subject_filter:

        attendance_records = attendance_records.filter(
            subject_id=subject_filter
        )

    if status_filter:

        attendance_records = attendance_records.filter(
            status=status_filter
        )

    subjects = Subject.objects.filter(
        active=True
    ).order_by(
        "code"
    )

    return render(
        request,
        "attendance/attendance_list.html",
        {
            "attendance_records": attendance_records,

            "subjects": subjects,

            "selected_date": date_filter,

            "selected_subject": subject_filter,

            "selected_status": status_filter,

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

    return render(
        request,
        "attendance/today_attendance.html",
        {
            "records": records,

            "today": today,
        }
    )


# =========================================================
# SUBJECT WISE ATTENDANCE
# =========================================================

@teacher_required
def subject_wise_attendance(request):

    subjects = Subject.objects.filter(
        active=True
    ).order_by(
        "code"
    )

    selected_subject = request.GET.get(
        "subject",
        ""
    ).strip()

    records = Attendance.objects.none()

    if selected_subject:

        records = Attendance.objects.select_related(
            "student",
            "subject"
        ).filter(
            subject_id=selected_subject
        ).order_by(
            "-date",
            "-time"
        )

    return render(
        request,
        "attendance/subject_wise.html",
        {
            "subjects": subjects,

            "records": records,

            "selected_subject": selected_subject,

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

    selected_student = request.GET.get(
        "student",
        ""
    ).strip()

    records = Attendance.objects.none()

    student = None

    if selected_student:

        try:

            student = Student.objects.get(
                id=selected_student
            )

            records = Attendance.objects.select_related(
                "subject"
            ).filter(
                student=student
            ).order_by(
                "-date",
                "-time"
            )

        except (
            Student.DoesNotExist,
            ValueError
        ):

            student = None

    return render(
        request,
        "attendance/student_history.html",
        {
            "students": students,

            "student": student,

            "records": records,

            "selected_student": selected_student,

        }
    )


# =========================================================
# EXPORT ATTENDANCE EXCEL
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

    date_filter = request.GET.get(
        "date",
        ""
    ).strip()

    subject_filter = request.GET.get(
        "subject",
        ""
    ).strip()

    if date_filter:

        records = records.filter(
            date=date_filter
        )

    if subject_filter:

        records = records.filter(
            subject_id=subject_filter
        )

    workbook = Workbook()

    worksheet = workbook.active

    worksheet.title = "Attendance"

    headers = [

        "Student Name",

        "Roll Number",

        "Course",

        "Year",

        "Branch",

        "Section",

        "Semester",

        "Subject",

        "Date",

        "Time",

        "Status",

        "Latitude",

        "Longitude",

        "Location Verified",

    ]

    worksheet.append(
        headers
    )

    for record in records:

        worksheet.append(

            [

                record.student.name,

                record.student.roll_no,

                record.student.course,

                record.student.year,

                record.student.branch,

                record.student.section,

                record.student.semester,

                (
                    str(record.subject)
                    if record.subject
                    else ""
                ),

                record.date,

                record.time,

                record.status,

                record.latitude,

                record.longitude,

                record.location_verified,

            ]

        )

    response = HttpResponse(

        content_type=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        )

    )

    response[
        "Content-Disposition"
    ] = (
        'attachment; filename="attendance_report.xlsx"'
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

                "error": "Only POST method is allowed."
            },
            status=405
        )

    session_id = request.POST.get(
        "session",
        ""
    ).strip()

    if not session_id:

        return JsonResponse(
            {
                "success": False,

                "error": "Session ID is required."
            },
            status=400
        )

    try:

        session_uuid = uuid.UUID(
            session_id
        )

    except ValueError:

        return JsonResponse(
            {
                "success": False,

                "error": "Invalid session ID."
            },
            status=400
        )

    try:

        session = AttendanceSession.objects.get(
            session_id=session_uuid
        )

    except AttendanceSession.DoesNotExist:

        return JsonResponse(
            {
                "success": False,

                "error": "Attendance session not found."
            },
            status=404
        )

    students = Student.objects.all()

    created_count = 0

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

                date=timezone.localdate(),

                time=timezone.localtime().time(),

                status="Absent",

                location_verified=False,

            )

            created_count += 1

    return JsonResponse(
        {
            "success": True,

            "message": (
                f"{created_count} students "
                "marked absent."
            ),

            "created": created_count,

        }
    )


# =========================================================
# CLEAN EXPIRED SESSIONS
# =========================================================

@teacher_required
def clean_expired_sessions(request):

    now = timezone.now()

    updated = AttendanceSession.objects.filter(

        active=True,

        expires_at__lte=now

    ).update(

        active=False

    )

    return JsonResponse(
        {
            "success": True,

            "updated": updated,

            "message": (
                f"{updated} expired session(s) "
                "deactivated."
            ),

        }
    )


# =========================================================
# END OF VIEWS.PY
# =========================================================