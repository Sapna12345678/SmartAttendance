
import uuid
import base64
from io import BytesIO
from math import radians, sin, cos, sqrt, atan2

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

import qrcode
from openpyxl import Workbook

from .models import (
    Student,
    Subject,
    AttendanceSession,
    Attendance,
)


# =====================================================
# HOME
# =====================================================

def home(request):
    return render(
        request,
        "attendance/home.html"
    )


# =====================================================
# PUBLIC HOST
# =====================================================

def get_public_host():

    from django.conf import settings

    host = getattr(
        settings,
        "SMART_ATTENDANCE_HOST",
        "smartattendance-edd1.onrender.com"
    )

    host = str(host)

    host = host.replace(
        "https://",
        ""
    ).replace(
        "http://",
        ""
    )

    host = host.rstrip("/")

    return host


# =====================================================
# DISTANCE CALCULATION
# =====================================================

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

        return 999999

    R = 6371000

    dlat = radians(
        lat2 - lat1
    )

    dlon = radians(
        lon2 - lon1
    )

    a = (
        sin(dlat / 2) ** 2
        +
        cos(radians(lat1))
        *
        cos(radians(lat2))
        *
        sin(dlon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a)
    )

    return R * c


# =====================================================
# REQUEST DATA
# =====================================================

def get_request_data(request):

    if request.content_type == "application/json":

        import json

        try:

            return json.loads(
                request.body.decode(
                    "utf-8"
                )
            )

        except Exception:

            return {}

    return request.POST


# =====================================================
# TEACHER LOGIN
# =====================================================

def teacher_login(request):

    if request.session.get(
        "teacher_logged_in"
    ):

        return redirect(
            "teacher_dashboard"
        )

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

            request.session[
                "teacher_logged_in"
            ] = True

            request.session[
                "teacher_id"
            ] = user.id

            request.session[
                "teacher_username"
            ] = user.username

            return redirect(
                "teacher_dashboard"
            )

        return render(
            request,
            "attendance/teacher_login.html",
            {
                "error":
                    "Invalid username or password."
            }
        )

    return render(
        request,
        "attendance/teacher_login.html"
    )


# =====================================================
# TEACHER LOGOUT
# =====================================================

def teacher_logout(request):

    request.session.pop(
        "teacher_logged_in",
        None
    )

    request.session.pop(
        "teacher_id",
        None
    )

    request.session.pop(
        "teacher_username",
        None
    )

    return redirect(
        "teacher_login"
    )


# =====================================================
# TEACHER REQUIRED
# =====================================================

def teacher_required(view_func):

    def wrapper(
        request,
        *args,
        **kwargs
    ):

        if not request.session.get(
            "teacher_logged_in"
        ):

            return redirect(
                "teacher_login"
            )

        return view_func(
            request,
            *args,
            **kwargs
        )

    return wrapper


# =====================================================
# TEACHER DASHBOARD
# =====================================================

@teacher_required
def teacher_dashboard(request):

    today = timezone.localdate()

    total_students = (
        Student.objects.count()
    )

    present_today = (
        Attendance.objects.filter(
            date=today,
            status="Present"
        ).count()
    )

    absent_today = (
        Attendance.objects.filter(
            date=today,
            status="Absent"
        ).count()
    )

    total_today = (
        present_today +
        absent_today
    )

    if total_today > 0:

        attendance_percentage = round(
            present_today /
            total_today *
            100,
            1
        )

    else:

        attendance_percentage = 0

    active_sessions = (
        AttendanceSession.objects.filter(
            active=True,
            expires_at__gt=timezone.now()
        )
        .select_related(
            "subject",
            "teacher"
        )
        .order_by(
            "-created_at"
        )
    )

    active_qr_count = (
        active_sessions.count()
    )

    context = {

        "total_students":
            total_students,

        "present_today":
            present_today,

        "absent_today":
            absent_today,

        "attendance_percentage":
            attendance_percentage,

        "attendance_percent":
            attendance_percentage,

        "active_sessions":
            active_sessions,

        "active_qr_count":
            active_qr_count,
    }

    return render(
        request,
        "attendance/teacher_dashboard.html",
        context
    )


# =====================================================
# STUDENTS
# =====================================================

@teacher_required
def students_page(request):

    students = (
        Student.objects.all()
        .order_by("roll_no")
    )

    return render(
        request,
        "attendance/students.html",
        {
            "students":
                students
        }
    )


# =====================================================
# GENERATE QR
# =====================================================

@teacher_required
def generate_qr(request):

    if request.method == "POST":

        subject_id = request.POST.get(
            "subject"
        )

        branch = request.POST.get(
            "branch",
            ""
        ).strip()

        section = request.POST.get(
            "section",
            ""
        ).strip()

        semester_value = request.POST.get(
            "semester",
            "3"
        )

        duration_value = request.POST.get(
            "duration",
            "60"
        )

    else:

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

        semester_value = request.GET.get(
            "semester",
            "3"
        )

        duration_value = request.GET.get(
            "duration",
            "60"
        )

    # -------------------------------------------------
    # SEMESTER
    # -------------------------------------------------

    try:

        semester = int(
            str(
                semester_value
            )
            .replace(
                "Semester",
                ""
            )
            .replace(
                "semester",
                ""
            )
            .strip()
        )

    except (
        ValueError,
        TypeError
    ):

        semester = 3

    # -------------------------------------------------
    # DURATION
    # -------------------------------------------------

    try:

        duration = int(
            duration_value
        )

    except (
        ValueError,
        TypeError
    ):

        duration = 60

    duration = max(
        30,
        min(
            duration,
            300
        )
    )

    # -------------------------------------------------
    # SUBJECT
    # -------------------------------------------------

    subject = None

    if subject_id:

        try:

            subject = (
                Subject.objects.get(
                    id=int(subject_id)
                )
            )

        except (
            Subject.DoesNotExist,
            ValueError,
            TypeError
        ):

            subject = None

    # -------------------------------------------------
    # DEACTIVATE OLD QR
    # -------------------------------------------------

    AttendanceSession.objects.filter(
        active=True
    ).update(
        active=False
    )

    # -------------------------------------------------
    # TEACHER
    # -------------------------------------------------

    teacher = None

    teacher_id = request.session.get(
        "teacher_id"
    )

    if teacher_id:

        try:

            teacher = (
                User.objects.get(
                    id=teacher_id
                )
            )

        except User.DoesNotExist:

            teacher = None

    # -------------------------------------------------
    # CREATE SESSION
    # -------------------------------------------------

    now = timezone.now()

    session = (
        AttendanceSession.objects.create(

            session_id=uuid.uuid4(),

            subject=subject,

            teacher=teacher,

            branch=branch,

            section=section,

            semester=semester,

            created_at=now,

            expires_at=(
                now +
                timezone.timedelta(
                    seconds=duration
                )
            ),

            active=True,
        )
    )

    # -------------------------------------------------
    # PUBLIC QR URL
    # -------------------------------------------------

    host = get_public_host()

    qr_url = (
        "https://"
        + host
        + "/scan/?session="
        + str(
            session.session_id
        )
    )

    # -------------------------------------------------
    # QR IMAGE
    # -------------------------------------------------

    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4
    )

    qr.add_data(
        qr_url
    )

    qr.make(
        fit=True
    )

    img = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    buffer = BytesIO()

    img.save(
        buffer,
        format="PNG"
    )

    qr_base64 = (
        base64.b64encode(
            buffer.getvalue()
        )
        .decode(
            "utf-8"
        )
    )

    qr_image_base64 = (
        "data:image/png;base64,"
        + qr_base64
    )

    # -------------------------------------------------
    # PROJECTOR
    # -------------------------------------------------

    return render(
        request,
        "attendance/projector.html",
        {

            "session":
                session,

            "session_id":
                str(
                    session.session_id
                ),

            "qr_image_base64":
                qr_image_base64,

            "qr_url":
                qr_url,

            "duration":
                duration,

            "expires_at":
                session.expires_at,
        }
    )


# =====================================================
# PROJECTOR
# =====================================================

@teacher_required
def projector(request):

    session_id = request.GET.get(
        "session"
    )

    session = None

    if session_id:

        try:

            session = (
                AttendanceSession.objects
                .select_related(
                    "subject"
                )
                .get(
                    session_id=session_id
                )
            )

        except (
            AttendanceSession.DoesNotExist,
            ValueError
        ):

            session = None

    return render(
        request,
        "attendance/projector.html",
        {

            "session":
                session,

            "session_id":
                (
                    str(
                        session.session_id
                    )
                    if session
                    else ""
                ),

            "duration":
                (
                    max(
                        0,
                        int(
                            (
                                session.expires_at -
                                timezone.now()
                            ).total_seconds()
                        )
                    )
                    if session
                    else 0
                ),
        }
    )


# =====================================================
# SCAN QR
# =====================================================

def scan_qr(request):

    session_id = request.GET.get(
        "session"
    )

    if not session_id:

        if request.GET.get(
            "data"
        ) == "1":

            return JsonResponse(
                {
                    "valid":
                        False,

                    "error":
                        "Session ID is missing."
                }
            )

        return render(
            request,
            "attendance/scan.html",
            {
                "error":
                    "Attendance session is missing."
            }
        )

    try:

        session = (
            AttendanceSession.objects
            .select_related(
                "subject"
            )
            .get(
                session_id=session_id
            )
        )

    except (
        AttendanceSession.DoesNotExist,
        ValueError
    ):

        if request.GET.get(
            "data"
        ) == "1":

            return JsonResponse(
                {
                    "valid":
                        False,

                    "error":
                        "Invalid attendance session."
                }
            )

        return render(
            request,
            "attendance/scan.html",
            {
                "error":
                    "Invalid Attendance QR."
            }
        )

    now = timezone.now()

    # -------------------------------------------------
    # EXPIRY
    # -------------------------------------------------

    if (
        not session.active
        or
        session.expires_at <= now
    ):

        if session.active:

            session.active = False

            session.save(
                update_fields=[
                    "active"
                ]
            )

        if request.GET.get(
            "data"
        ) == "1":

            return JsonResponse(
                {
                    "valid":
                        False,

                    "error":
                        "QR code has expired."
                }
            )

        return render(
            request,
            "attendance/scan.html",
            {
                "error":
                    "QR code has expired."
            }
        )

    # -------------------------------------------------
    # TIME LEFT
    # -------------------------------------------------

    time_left = max(
        0,
        int(
            (
                session.expires_at -
                now
            ).total_seconds()
        )
    )

    subject_name = "General"

    if session.subject:

        subject_name = str(
            session.subject
        )

    # -------------------------------------------------
    # JSON DATA
    # -------------------------------------------------

    if request.GET.get(
        "data"
    ) == "1":

        return JsonResponse(
            {

                "valid":
                    True,

                "session_id":
                    str(
                        session.session_id
                    ),

                "subject":
                    subject_name,

                "branch":
                    session.branch,

                "section":
                    session.section,

                "semester":
                    session.semester,

                "time_left":
                    time_left,
            }
        )

    # -------------------------------------------------
    # SCAN PAGE
    # -------------------------------------------------

    return render(
        request,
        "attendance/scan.html",
        {

            "session":
                session,

            "session_id":
                str(
                    session.session_id
                ),

            "subject":
                subject_name,

            "time_left":
                time_left,
        }
    )


# =====================================================
# MARK ATTENDANCE
# =====================================================

@csrf_exempt
def mark_attendance(request):

    if request.method != "POST":

        return JsonResponse(
            {
                "success":
                    False,

                "error":
                    "POST request required."
            },
            status=405
        )

    data = get_request_data(
        request
    )

    session_id = (
        data.get("session")
        or
        data.get("session_id")
    )

    latitude = data.get(
        "latitude"
    )

    longitude = data.get(
        "longitude"
    )

    # -------------------------------------------------
    # SESSION REQUIRED
    # -------------------------------------------------

    if not session_id:

        return JsonResponse(
            {
                "success":
                    False,

                "error":
                    "Attendance session is missing."
            },
            status=400
        )

    # -------------------------------------------------
    # GET SESSION
    # -------------------------------------------------

    try:

        session = (
            AttendanceSession.objects
            .select_related(
                "subject"
            )
            .get(
                session_id=session_id
            )
        )

    except (
        AttendanceSession.DoesNotExist,
        ValueError
    ):

        return JsonResponse(
            {
                "success":
                    False,

                "error":
                    "Invalid attendance session."
            },
            status=404
        )

    # -------------------------------------------------
    # EXPIRY
    # -------------------------------------------------

    if (
        not session.active
        or
        session.expires_at <= timezone.now()
    ):

        if session.active:

            session.active = False

            session.save(
                update_fields=[
                    "active"
                ]
            )

        return JsonResponse(
            {
                "success":
                    False,

                "error":
                    "QR code has expired."
            },
            status=410
        )

    # -------------------------------------------------
    # STUDENT
    # -------------------------------------------------

    student = None

    if request.user.is_authenticated:

        try:

            student = (
                request.user.student_profile
            )

        except Student.DoesNotExist:

            student = None

    # -------------------------------------------------
    # FALLBACK STUDENT ID
    # -------------------------------------------------

    student_id = data.get(
        "student_id"
    )

    if (
        student is None
        and
        student_id
    ):

        try:

            student = (
                Student.objects.get(
                    id=student_id
                )
            )

        except (
            Student.DoesNotExist,
            ValueError,
            TypeError
        ):

            student = None

    # -------------------------------------------------
    # LOGIN REQUIRED
    # -------------------------------------------------

    if student is None:

        return JsonResponse(
            {
                "success":
                    False,

                "error":
                    "Student login required."
            },
            status=401
        )

    # -------------------------------------------------
    # BRANCH
    # -------------------------------------------------

    if (
        session.branch
        and
        student.branch
        and
        session.branch.strip().lower()
        !=
        student.branch.strip().lower()
    ):

        return JsonResponse(
            {
                "success":
                    False,

                "error":
                    "Student branch does not match."
            },
            status=403
        )

    # -------------------------------------------------
    # SECTION
    # -------------------------------------------------

    if (
        session.section
        and
        student.section
        and
        session.section.strip().lower()
        !=
        student.section.strip().lower()
    ):

        return JsonResponse(
            {
                "success":
                    False,

                "error":
                    "Student section does not match."
            },
            status=403
        )

    # -------------------------------------------------
    # SEMESTER
    # -------------------------------------------------

    if (
        session.semester is not None
        and
        student.semester is not None
    ):

        try:

            session_semester = int(
                session.semester
            )

            student_semester = int(
                student.semester
            )

        except (
            ValueError,
            TypeError
        ):

            session_semester = str(
                session.semester
            ).strip().lower()

            student_semester = str(
                student.semester
            ).strip().lower()

        if (
            session_semester
            !=
            student_semester
        ):

            return JsonResponse(
                {
                    "success":
                        False,

                    "error":
                        "Student semester does not match."
                },
                status=403
            )

    # =================================================
    # GPS
    # =================================================

    from django.conf import settings

    college_lat = float(
        getattr(
            settings,
            "ATTENDANCE_LATITUDE",
            25.342787
        )
    )

    college_lon = float(
        getattr(
            settings,
            "ATTENDANCE_LONGITUDE",
            81.902116
        )
    )

    radius = float(
        getattr(
            settings,
            "ATTENDANCE_RADIUS_METERS",
            300
        )
    )

    if (
        latitude is None
        or
        longitude is None
    ):

        return JsonResponse(
            {
                "success":
                    False,

                "error":
                    "Location is required."
            },
            status=400
        )

    try:

        student_lat = float(
            latitude
        )

        student_lon = float(
            longitude
        )

    except (
        ValueError,
        TypeError
    ):

        return JsonResponse(
            {
                "success":
                    False,

                "error":
                    "Invalid GPS coordinates."
            },
            status=400
        )

    distance = calculate_distance(
        college_lat,
        college_lon,
        student_lat,
        student_lon
    )

    location_verified = (
        distance <= radius
    )

    # -------------------------------------------------
    # PREVENT DUPLICATE ATTENDANCE
    # -------------------------------------------------

    today = timezone.localdate()

    existing = (
        Attendance.objects.filter(
            student=student,
            date=today,
            session_id=session.session_id
        )
        .first()
    )

    if existing:

        return JsonResponse(
            {

                "success":
                    True,

                "already_marked":
                    True,

                "status":
                    existing.status,

                "location_verified":
                    existing.location_verified,

                "distance":
                    round(
                        distance,
                        2
                    ),
            }
        )

    # -------------------------------------------------
    # PRESENT / ABSENT
    # -------------------------------------------------

    status = (
        "Present"
        if location_verified
        else
        "Absent"
    )

    attendance = (
        Attendance.objects.create(

            student=student,

            session_id=
                session.session_id,

            subject=
                session.subject,

            date=today,

            time=
                timezone.localtime().time(),

            status=status,

            latitude=
                student_lat,

            longitude=
                student_lon,

            location_verified=
                location_verified,
        )
    )

    # -------------------------------------------------
    # RESPONSE
    # -------------------------------------------------

    return JsonResponse(
        {

            "success":
                True,

            "status":
                attendance.status,

            "location_verified":
                attendance.location_verified,

            "distance":
                round(
                    distance,
                    2
                ),

            "message":
                (
                    "Attendance marked Present."
                    if location_verified
                    else
                    "You are outside the attendance area. Marked Absent."
                ),
        }
    )


# =====================================================
# ATTENDANCE LIST
# =====================================================

@teacher_required
def attendance_list(request):

    records = (
        Attendance.objects
        .select_related(
            "student",
            "subject"
        )
        .order_by(
            "-date",
            "-time"
        )
    )

    return render(
        request,
        "attendance/attendance_list.html",
        {
            "records":
                records
        }
    )


# =====================================================
# TODAY ATTENDANCE
# =====================================================

@teacher_required
def today_attendance(request):

    today = timezone.localdate()

    records = (
        Attendance.objects
        .select_related(
            "student",
            "subject"
        )
        .filter(
            date=today
        )
        .order_by(
            "-time"
        )
    )

    return render(
        request,
        "attendance/today_attendance.html",
        {
            "records":
                records,

            "today":
                today,
        }
    )


# =====================================================
# SUBJECT WISE
# =====================================================

@teacher_required
def subject_wise_attendance(request):

    subject_id = request.GET.get(
        "subject"
    )

    records = (
        Attendance.objects
        .select_related(
            "student",
            "subject"
        )
    )

    if subject_id:

        try:

            records = records.filter(
                subject_id=int(
                    subject_id
                )
            )

        except (
            ValueError,
            TypeError
        ):

            pass

    subjects = (
        Subject.objects
        .filter(
            active=True
        )
        .order_by(
            "code",
            "name"
        )
    )

    return render(
        request,
        "attendance/subject_wise.html",
        {

            "records":
                records.order_by(
                    "-date",
                    "-time"
                ),

            "subjects":
                subjects,

            "selected_subject":
                subject_id,
        }
    )


# =====================================================
# STUDENT HISTORY
# =====================================================

@teacher_required
def student_history(request):

    student_id = request.GET.get(
        "student"
    )

    records = (
        Attendance.objects
        .select_related(
            "student",
            "subject"
        )
    )

    if student_id:

        try:

            records = records.filter(
                student_id=int(
                    student_id
                )
            )

        except (
            ValueError,
            TypeError
        ):

            pass

    students = (
        Student.objects
        .all()
        .order_by(
            "roll_no"
        )
    )

    return render(
        request,
        "attendance/student_history.html",
        {

            "records":
                records.order_by(
                    "-date",
                    "-time"
                ),

            "students":
                students,

            "selected_student":
                student_id,
        }
    )


# =====================================================
# EXPORT EXCEL
# =====================================================

@teacher_required
def export_attendance_excel(request):

    records = (
        Attendance.objects
        .select_related(
            "student",
            "subject"
        )
        .order_by(
            "date",
            "time"
        )
    )

    workbook = Workbook()

    sheet = workbook.active

    sheet.title = "Attendance"

    sheet.append(
        [
            "Date",
            "Time",
            "Student Name",
            "Roll No",
            "Course",
            "Branch",
            "Section",
            "Semester",
            "Subject",
            "Status",
            "Latitude",
            "Longitude",
            "Location Verified",
        ]
    )

    for record in records:

        subject_name = ""

        if record.subject:

            subject_name = str(
                record.subject
            )

        sheet.append(
            [
                record.date,
                record.time,

                record.student.name,

                record.student.roll_no,

                record.student.course,

                record.student.branch,

                record.student.section,

                record.student.semester,

                subject_name,

                record.status,

                record.latitude,

                record.longitude,

                record.location_verified,
            ]
        )

    response = HttpResponse(
        content_type=
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
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


# =====================================================
# MARK ABSENT STUDENTS
# =====================================================

@teacher_required
def mark_absent_students(request):

    today = timezone.localdate()

    students = Student.objects.all()

    created_count = 0

    for student in students:

        exists = (
            Attendance.objects.filter(
                student=student,
                date=today
            )
            .exists()
        )

        if not exists:

            Attendance.objects.create(

                student=student,

                date=today,

                time=
                    timezone.localtime().time(),

                status="Absent",

                location_verified=False,
            )

            created_count += 1

    return JsonResponse(
        {
            "success":
                True,

            "created":
                created_count,
        }
    )


# =====================================================
# CLEAN EXPIRED SESSIONS
# =====================================================

@teacher_required
def clean_expired_sessions(request):

    updated = (
        AttendanceSession.objects
        .filter(
            active=True,
            expires_at__lte=timezone.now()
        )
        .update(
            active=False
        )
    )

    return JsonResponse(
        {
            "success":
                True,

            "deactivated":
                updated,
        }
    )

