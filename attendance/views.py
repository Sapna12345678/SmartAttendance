
import uuid
import base64
from io import BytesIO
from math import radians, sin, cos, sqrt, atan2

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Q
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


# ============================================================
# PUBLIC HOST
# ============================================================

def get_public_host():

    host = getattr(
        settings,
        "SMART_ATTENDANCE_HOST",
        "smartattendance-edd1.onrender.com"
    )

    host = str(host).strip()

    host = host.replace(
        "https://",
        ""
    )

    host = host.replace(
        "http://",
        ""
    )

    host = host.rstrip("/")

    return host


# ============================================================
# TEACHER REQUIRED
# ============================================================

def teacher_required(view_func):

    def wrapper(request, *args, **kwargs):

        if not request.session.get(
            "teacher_logged_in",
            False
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


# ============================================================
# HOME
# ============================================================

def home(request):

    if request.user.is_authenticated:

        if hasattr(
            request.user,
            "student_profile"
        ):
            return redirect(
                "student_home"
            )

        if request.session.get(
            "teacher_logged_in",
            False
        ):
            return redirect(
                "teacher_dashboard"
            )

    return render(
        request,
        "attendance/home.html"
    )


# ============================================================
# TEACHER LOGIN
# ============================================================

def teacher_login(request):

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

            login(
                request,
                user
            )

            return redirect(
                "teacher_dashboard"
            )

        return render(
            request,
            "attendance/teacher_login.html",
            {
                "error":
                    "Invalid Teacher ID or Password."
            }
        )

    return render(
        request,
        "attendance/teacher_login.html"
    )


# ============================================================
# TEACHER LOGOUT
# ============================================================

def teacher_logout(request):

    request.session[
        "teacher_logged_in"
    ] = False

    request.session.pop(
        "teacher_id",
        None
    )

    logout(request)

    return redirect(
        "teacher_login"
    )


# ============================================================
# TEACHER DASHBOARD
# ============================================================

@teacher_required
def teacher_dashboard(request):

    today = timezone.localdate()

    today_records = Attendance.objects.filter(
        date=today
    )

    total_students = Student.objects.count()

    present_today = (
        today_records
        .filter(
            status="Present"
        )
        .count()
    )

    absent_today = (
        today_records
        .filter(
            status="Absent"
        )
        .count()
    )

    if total_students:

        attendance_percentage = round(
            (
                present_today
                / total_students
            ) * 100,
            2
        )

    else:

        attendance_percentage = 0

    active_sessions = (
        AttendanceSession.objects
        .filter(
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

    recent_attendance = (
        Attendance.objects
        .select_related(
            "student",
            "subject"
        )
        .order_by(
            "-date",
            "-time"
        )[:10]
    )

    return render(
        request,
        "attendance/teacher_dashboard.html",
        {
            "total_students":
                total_students,

            "present_today":
                present_today,

            "absent_today":
                absent_today,

            "attendance_percentage":
                attendance_percentage,

            "active_sessions":
                active_sessions,

            "active_qr_count":
                active_qr_count,

            "recent_attendance":
                recent_attendance,
        }
    )


# ============================================================
# GENERATE QR
# ============================================================

@teacher_required
def generate_qr(request):

    # --------------------------------------------------------
    # SHOW FORM
    # --------------------------------------------------------

    if (
        request.method == "GET"
        and request.GET.get(
            "generate"
        ) != "1"
    ):

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
            "attendance/generate_qr.html",
            {
                "subjects":
                    subjects,

                "duration":
                    60,
            }
        )

    # --------------------------------------------------------
    # READ FORM DATA
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # SUBJECT
    # --------------------------------------------------------

    subject = None

    if subject_id:

        try:

            subject = Subject.objects.get(
                id=int(subject_id)
            )

        except (
            Subject.DoesNotExist,
            ValueError,
            TypeError
        ):

            subject = None

    if subject is None:

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
            "attendance/generate_qr.html",
            {
                "subjects":
                    subjects,

                "error":
                    "Please select a valid subject.",

                "selected_branch":
                    branch,

                "selected_section":
                    section,

                "selected_semester":
                    str(
                        semester_value
                    ),

                "duration":
                    60,
            }
        )

    # --------------------------------------------------------
    # BRANCH
    # --------------------------------------------------------

    if not branch:

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
            "attendance/generate_qr.html",
            {
                "subjects":
                    subjects,

                "selected_subject":
                    subject,

                "selected_branch":
                    branch,

                "selected_section":
                    section,

                "selected_semester":
                    str(
                        semester_value
                    ),

                "duration":
                    60,

                "error":
                    "Please enter the branch.",
            }
        )

    # --------------------------------------------------------
    # SECTION
    # --------------------------------------------------------

    if not section:

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
            "attendance/generate_qr.html",
            {
                "subjects":
                    subjects,

                "selected_subject":
                    subject,

                "selected_branch":
                    branch,

                "selected_section":
                    section,

                "selected_semester":
                    str(
                        semester_value
                    ),

                "duration":
                    60,

                "error":
                    "Please enter the section.",
            }
        )

    # --------------------------------------------------------
    # SEMESTER
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # DURATION
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # DEACTIVATE OLD SESSIONS
    # --------------------------------------------------------

    AttendanceSession.objects.filter(
        active=True
    ).update(
        active=False
    )

    # --------------------------------------------------------
    # TEACHER
    # --------------------------------------------------------

    teacher = None

    teacher_id = request.session.get(
        "teacher_id"
    )

    if teacher_id:

        try:

            teacher = User.objects.get(
                id=teacher_id
            )

        except User.DoesNotExist:

            teacher = None

    # --------------------------------------------------------
    # CREATE SESSION
    # --------------------------------------------------------

    now = timezone.now()

    session = AttendanceSession.objects.create(

        session_id=
            uuid.uuid4(),

        subject=
            subject,

        teacher=
            teacher,

        branch=
            branch,

        section=
            section,

        semester=
            semester,

        created_at=
            now,

        expires_at=(
            now +
            timezone.timedelta(
                seconds=duration
            )
        ),

        active=True,
    )

    # --------------------------------------------------------
    # SCAN URL
    # --------------------------------------------------------

    host = get_public_host()

    qr_url = (
        "https://"
        + host
        + "/scan/?session="
        + str(
            session.session_id
        )
    )

    # --------------------------------------------------------
    # CREATE QR
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # BASE64
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # RENDER PROJECTOR
    # --------------------------------------------------------

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

            "scan_url":
                qr_url,

            "duration":
                duration,

            "remaining_seconds":
                duration,

            "filename":
                (
                    "attendance_qr_"
                    + str(
                        session.session_id
                    )
                    + ".png"
                ),

            "expires_at":
                session.expires_at,

            "subject_name":
                str(
                    subject
                ),

            "branch":
                branch,

            "section":
                section,

            "semester":
                semester,
        }
    )


# ============================================================
# PROJECTOR
# ============================================================

@teacher_required
def projector(request):

    session_id = request.GET.get(
        "session"
    )

    if not session_id:

        return HttpResponse(
            "Session ID is required.",
            status=400
        )

    try:

        session = (
            AttendanceSession.objects
            .select_related(
                "subject",
                "teacher"
            )
            .get(
                session_id=session_id
            )
        )

    except (
        AttendanceSession.DoesNotExist,
        ValueError
    ):

        return HttpResponse(
            "Attendance session not found.",
            status=404
        )

    now = timezone.now()

    if (
        not session.active
        or session.expires_at <= now
    ):

        session.active = False

        session.save(
            update_fields=[
                "active"
            ]
        )

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

                "expired":
                    True,

                "duration":
                    0,

                "remaining_seconds":
                    0,
            }
        )

    remaining_seconds = max(
        0,
        int(
            (
                session.expires_at
                - now
            ).total_seconds()
        )
    )

    host = get_public_host()

    scan_url = (
        "https://"
        + host
        + "/scan/?session="
        + str(
            session.session_id
        )
    )

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

            "scan_url":
                scan_url,

            "duration":
                remaining_seconds,

            "remaining_seconds":
                remaining_seconds,

            "subject_name": (
                str(
                    session.subject
                )
                if session.subject
                else "General"
            ),

            "branch":
                session.branch
                or "Not specified",

            "section":
                session.section
                or "Not specified",

            "semester":
                session.semester,

            "expires_at":
                session.expires_at,

            "expired":
                False,
        }
    )


# ============================================================
# SCAN QR
# ============================================================

def scan_qr(request):

    session_id = request.GET.get(
        "session"
    )

    if not session_id:

        return JsonResponse(
            {
                "valid": False,
                "error":
                    "QR session is missing."
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
                session_id=session_id
            )
        )

    except (
        AttendanceSession.DoesNotExist,
        ValueError
    ):

        return JsonResponse(
            {
                "valid": False,
                "error":
                    "Invalid attendance QR."
            },
            status=404
        )

    now = timezone.now()

    if (
        not session.active
        or session.expires_at <= now
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
                "valid": False,
                "error":
                    "QR code has expired."
            }
        )

    remaining_seconds = max(
        0,
        int(
            (
                session.expires_at
                - now
            ).total_seconds()
        )
    )

    subject_name = "General"

    if session.subject:

        subject_name = str(
            session.subject
        )

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
                session.branch
                or "Not specified",

            "section":
                session.section
                or "Not specified",

            "semester":
                session.semester,

            "time_left":
                remaining_seconds,
        }
    )


# ============================================================
# MARK ATTENDANCE
# ============================================================

@csrf_exempt
def mark_attendance(request):

    if request.method != "POST":

        return JsonResponse(
            {
                "success": False,
                "error":
                    "POST request required."
            },
            status=405
        )

    import json

    try:

        data = json.loads(
            request.body.decode(
                "utf-8"
            )
        )

    except Exception:

        data = request.POST

    session_id = data.get(
        "session_id"
    )

    latitude = data.get(
        "latitude"
    )

    longitude = data.get(
        "longitude"
    )

    if not session_id:

        return JsonResponse(
            {
                "success": False,
                "error":
                    "Session ID is required."
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
                session_id=session_id
            )
        )

    except (
        AttendanceSession.DoesNotExist,
        ValueError
    ):

        return JsonResponse(
            {
                "success": False,
                "error":
                    "Invalid attendance session."
            },
            status=404
        )

    # --------------------------------------------------------
    # EXPIRY
    # --------------------------------------------------------

    now = timezone.now()

    if (
        not session.active
        or session.expires_at <= now
    ):

        session.active = False

        session.save(
            update_fields=[
                "active"
            ]
        )

        return JsonResponse(
            {
                "success": False,
                "error":
                    "QR code has expired."
            },
            status=400
        )

    # --------------------------------------------------------
    # STUDENT
    # --------------------------------------------------------

    student = None

    if request.user.is_authenticated:

        try:

            student = request.user.student_profile

        except Student.DoesNotExist:

            student = None

    # Optional fallback
    if student is None:

        student_id = data.get(
            "student_id"
        )

        if student_id:

            try:

                student = Student.objects.get(
                    id=student_id
                )

            except Student.DoesNotExist:

                student = None

    if student is None:

        return JsonResponse(
            {
                "success": False,
                "error":
                    "Student login required."
            },
            status=401
        )

    # --------------------------------------------------------
    # STUDENT ELIGIBILITY
    # --------------------------------------------------------

    if (
        session.branch
        and student.branch
        and session.branch.lower()
        != student.branch.lower()
    ):

        return JsonResponse(
            {
                "success": False,
                "error":
                    "Student branch does not match this QR."
            },
            status=400
        )

    if (
        session.section
        and student.section
        and session.section.lower()
        != student.section.lower()
    ):

        return JsonResponse(
            {
                "success": False,
                "error":
                    "Student section does not match this QR."
            },
            status=400
        )

    try:

        student_semester = int(
            str(
                student.semester
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

        student_semester = None

    if (
        session.semester
        and student_semester
        and int(
            session.semester
        )
        != student_semester
    ):

        return JsonResponse(
            {
                "success": False,
                "error":
                    "Student semester does not match this QR."
            },
            status=400
        )

    # --------------------------------------------------------
    # GPS
    # --------------------------------------------------------

    try:

        user_latitude = float(
            latitude
        )

        user_longitude = float(
            longitude
        )

    except (
        ValueError,
        TypeError
    ):

        return JsonResponse(
            {
                "success": False,
                "error":
                    "Valid GPS coordinates are required."
            },
            status=400
        )

    # --------------------------------------------------------
    # COLLEGE LOCATION
    # --------------------------------------------------------

    attendance_latitude = float(
        getattr(
            settings,
            "ATTENDANCE_LATITUDE",
            25.342787
        )
    )

    attendance_longitude = float(
        getattr(
            settings,
            "ATTENDANCE_LONGITUDE",
            81.902116
        )
    )

    attendance_radius = float(
        getattr(
            settings,
            "ATTENDANCE_RADIUS_METERS",
            300
        )
    )

    # --------------------------------------------------------
    # DISTANCE
    # --------------------------------------------------------

    def calculate_distance(
        lat1,
        lon1,
        lat2,
        lon2
    ):

        earth_radius = 6371000

        dlat = radians(
            lat2 - lat1
        )

        dlon = radians(
            lon2 - lon1
        )

        a = (
            sin(dlat / 2) ** 2
            +
            cos(
                radians(lat1)
            )
            *
            cos(
                radians(lat2)
            )
            *
            sin(dlon / 2) ** 2
        )

        c = 2 * atan2(
            sqrt(a),
            sqrt(1 - a)
        )

        return (
            earth_radius * c
        )

    distance = calculate_distance(
        attendance_latitude,
        attendance_longitude,
        user_latitude,
        user_longitude
    )

    location_verified = (
        distance <= attendance_radius
    )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    if location_verified:

        status = "Present"

    else:

        status = "Absent"

    # --------------------------------------------------------
    # DUPLICATE CHECK
    # --------------------------------------------------------

    today = timezone.localdate()

    duplicate = Attendance.objects.filter(
        student=student,
        session_id=session.session_id,
        date=today
    ).first()

    if duplicate:

        return JsonResponse(
            {
                "success": True,

                "status":
                    duplicate.status,

                "message":
                    (
                        "Attendance already recorded."
                    ),

                "location_verified":
                    duplicate.location_verified,

                "distance":
                    round(
                        distance,
                        2
                    ),
            }
        )

    # --------------------------------------------------------
    # CREATE ATTENDANCE
    # --------------------------------------------------------

    attendance = Attendance.objects.create(

        student=
            student,

        session_id=
            session.session_id,

        subject=
            session.subject,

        date=
            today,

        time=
            timezone.localtime().time(),

        status=
            status,

        latitude=
            user_latitude,

        longitude=
            user_longitude,

        location_verified=
            location_verified,
    )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    if status == "Present":

        message = (
            "Attendance marked PRESENT."
        )

    else:

        message = (
            "Attendance marked ABSENT "
            "because you are outside "
            "the attendance area."
        )

    return JsonResponse(
        {
            "success":
                True,

            "status":
                status,

            "message":
                message,

            "location_verified":
                location_verified,

            "distance":
                round(
                    distance,
                    2
                ),

            "attendance_id":
                attendance.id,
        }
    )


# ============================================================
# STUDENT LOGIN
# ============================================================

def student_login(request):

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

            try:

                student = user.student_profile

            except Student.DoesNotExist:

                student = None

            if student:

                login(
                    request,
                    user
                )

                return redirect(
                    "student_home"
                )

        return render(
            request,
            "attendance/student_login.html",
            {
                "error":
                    "Invalid Student ID or Password."
            }
        )

    return render(
        request,
        "attendance/student_login.html"
    )


# ============================================================
# STUDENT HOME
# ============================================================

def student_home(request):

    if not request.user.is_authenticated:

        return redirect(
            "student_login"
        )

    try:

        student = request.user.student_profile

    except Student.DoesNotExist:

        return redirect(
            "student_login"
        )

    records = Attendance.objects.filter(
        student=student
    )

    total_records = records.count()

    present_count = records.filter(
        status="Present"
    ).count()

    absent_count = records.filter(
        status="Absent"
    ).count()

    if total_records:

        attendance_percentage = round(
            (
                present_count
                / total_records
            ) * 100,
            2
        )

    else:

        attendance_percentage = 0

    return render(
        request,
        "attendance/student_home.html",
        {
            "student":
                student,

            "records":
                records.order_by(
                    "-date",
                    "-time"
                ),

            "total_records":
                total_records,

            "present_count":
                present_count,

            "absent_count":
                absent_count,

            "attendance_percentage":
                attendance_percentage,
        }
    )


# ============================================================
# STUDENT LOGOUT
# ============================================================

def student_logout(request):

    logout(request)

    return redirect(
        "student_login"
    )


# ============================================================
# TODAY ATTENDANCE
# ============================================================

@teacher_required
def today_attendance(request):

    today = timezone.localdate()

    records = (
        Attendance.objects
        .filter(
            date=today
        )
        .select_related(
            "student",
            "subject"
        )
        .order_by(
            "-time"
        )
    )

    total_students = records.count()

    present_count = records.filter(
        status="Present"
    ).count()

    absent_count = records.filter(
        status="Absent"
    ).count()

    if total_students:

        attendance_percentage = round(
            (
                present_count
                / total_students
            ) * 100,
            2
        )

    else:

        attendance_percentage = 0

    return render(
        request,
        "attendance/today_attendance.html",
        {
            "records":
                records,

            "today":
                today,

            "total_students":
                total_students,

            "present_count":
                present_count,

            "absent_count":
                absent_count,

            "attendance_percentage":
                attendance_percentage,
        }
    )


# ============================================================
# ATTENDANCE LIST
# ============================================================

@teacher_required
def attendance_list(request):

    selected_date = request.GET.get(
        "date"
    )

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if selected_date:

        records = Attendance.objects.filter(
            date=selected_date
        )

    else:

        records = Attendance.objects.all()

    if search:

        records = records.filter(

            Q(
                student__name__icontains=
                    search
            )

            |

            Q(
                student__roll_no__icontains=
                    search
            )

            |

            Q(
                subject__name__icontains=
                    search
            )

            |

            Q(
                subject__code__icontains=
                    search
            )
        )

    records = (
        records
        .select_related(
            "student",
            "subject"
        )
        .order_by(
            "-date",
            "-time"
        )
    )

    total_students = records.count()

    present_count = records.filter(
        status="Present"
    ).count()

    absent_count = records.filter(
        status="Absent"
    ).count()

    if total_students:

        attendance_percentage = round(
            (
                present_count
                / total_students
            ) * 100,
            2
        )

    else:

        attendance_percentage = 0

    return render(
        request,
        "attendance/attendance_list.html",
        {
            "attendances":
                records,

            "records":
                records,

            "selected_date":
                selected_date,

            "search":
                search,

            "total_students":
                total_students,

            "present_count":
                present_count,

            "absent_count":
                absent_count,

            "attendance_percentage":
                attendance_percentage,
        }
    )


# ============================================================
# SUBJECT WISE ATTENDANCE
# ============================================================

@teacher_required
def subject_wise_attendance(request):

    subjects = Subject.objects.filter(
        active=True
    ).order_by(
        "code",
        "name"
    )

    subject_id = request.GET.get(
        "subject"
    )

    selected_subject = None

    student_summary = []

    records = Attendance.objects.none()

    if subject_id:

        try:

            selected_subject = (
                Subject.objects.get(
                    id=subject_id
                )
            )

        except (
            Subject.DoesNotExist,
            ValueError,
            TypeError
        ):

            selected_subject = None

    if selected_subject:

        records = (
            Attendance.objects
            .filter(
                subject=selected_subject
            )
            .select_related(
                "student",
                "subject"
            )
            .order_by(
                "-date",
                "-time"
            )
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
                    2
                )
                if total
                else 0
            )

            student_summary.append(
                {
                    "student":
                        student,

                    "total":
                        total,

                    "present":
                        present,

                    "absent":
                        absent,

                    "percentage":
                        percentage,
                }
            )

    return render(
        request,
        "attendance/subject_wise.html",
        {
            "subjects":
                subjects,

            "selected_subject":
                selected_subject,

            "student_summary":
                student_summary,

            "records":
                records,
        }
    )


# ============================================================
# STUDENT HISTORY
# ============================================================

@teacher_required
def student_history(request):

    students = Student.objects.all().order_by(
        "roll_no"
    )

    student_id = request.GET.get(
        "student"
    )

    student = None

    records = Attendance.objects.none()

    total = 0
    present = 0
    absent = 0
    percentage = 0

    if student_id:

        try:

            student = Student.objects.get(
                id=student_id
            )

        except (
            Student.DoesNotExist,
            ValueError,
            TypeError
        ):

            student = None

    if student:

        records = (
            Attendance.objects
            .filter(
                student=student
            )
            .select_related(
                "subject"
            )
            .order_by(
                "-date",
                "-time"
            )
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
                (
                    present
                    / total
                ) * 100,
                2
            )
            if total
            else 0
        )

    return render(
        request,
        "attendance/student_history.html",
        {
            "students":
                students,

            "student":
                student,

            "records":
                records,

            "total":
                total,

            "present":
                present,

            "absent":
                absent,

            "percentage":
                percentage,
        }
    )


# ============================================================
# STUDENTS
# ============================================================

@teacher_required
def students(request):

    student_list = Student.objects.all().order_by(
        "roll_no"
    )

    return render(
        request,
        "attendance/students.html",
        {
            "students":
                student_list
        }
    )


# ============================================================
# REPORTS
# ============================================================

@teacher_required
def reports(request):

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
            2
        )
        if total
        else 0
    )

    return render(
        request,
        "attendance/reports.html",
        {
            "records":
                records,

            "total":
                total,

            "present":
                present,

            "absent":
                absent,

            "percentage":
                percentage,
        }
    )


# ============================================================
# EXPORT ATTENDANCE EXCEL
# ============================================================

@teacher_required
def export_attendance(request):

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

    workbook = Workbook()

    sheet = workbook.active

    sheet.title = "Attendance"

    headers = [
        "Student Name",
        "Roll Number",
        "Course",
        "Year",
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
    ]

    sheet.append(
        headers
    )

    for record in records:

        student = record.student

        subject = record.subject

        sheet.append(
            [
                student.name
                if student
                else "",

                student.roll_no
                if student
                else "",

                student.course
                if student
                else "",

                student.year
                if student
                else "",

                student.branch
                if student
                else "",

                student.section
                if student
                else "",

                student.semester
                if student
                else "",

                subject.name
                if subject
                else "",

                subject.code
                if subject
                else "",

                record.date,

                record.time,

                record.status,

                record.latitude,

                record.longitude,

                (
                    "Yes"
                    if record.location_verified
                    else "No"
                ),
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
        'attachment; '
        'filename="attendance_report.xlsx"'
    )

    workbook.save(
        response
    )

    return response


# ============================================================
# MARK ABSENT
# ============================================================

@teacher_required
def mark_absent(request):

    if request.method != "POST":

        return redirect(
            "attendance_list"
        )

    attendance_id = request.POST.get(
        "attendance_id"
    )

    try:

        attendance = Attendance.objects.get(
            id=attendance_id
        )

        attendance.status = "Absent"

        attendance.save(
            update_fields=[
                "status"
            ]
        )

    except (
        Attendance.DoesNotExist,
        ValueError,
        TypeError
    ):

        pass

    return redirect(
        "attendance_list"
    )


# ============================================================
# CLEAN EXPIRED SESSIONS
# ============================================================

@teacher_required
def clean_expired_sessions(request):

    AttendanceSession.objects.filter(
        active=True,
        expires_at__lte=timezone.now()
    ).update(
        active=False
    )

    return redirect(
        "teacher_dashboard"
    )


# ============================================================
# PROFILE
# ============================================================

@teacher_required
def profile(request):

    teacher = None

    teacher_id = request.session.get(
        "teacher_id"
    )

    if teacher_id:

        try:

            teacher = User.objects.get(
                id=teacher_id
            )

        except User.DoesNotExist:

            teacher = None

    return render(
        request,
        "attendance/profile.html",
        {
            "teacher":
                teacher
        }
    )
# ============================================================
# STUDENTS PAGE
# ============================================================

@teacher_required
def students_page(request):

    student_list = (
        Student.objects
        .all()
        .order_by("roll_no")
    )

    return render(
        request,
        "attendance/students.html",
        {
            "students": student_list
        }
    )
# ============================================================
# EXPORT ATTENDANCE EXCEL - URL COMPATIBILITY
# ============================================================

@teacher_required
def export_attendance_excel(request):
    return export_attendance(request)
# ============================================================
# MARK ABSENT STUDENTS - URL COMPATIBILITY
# ============================================================

@teacher_required
def mark_absent_students(request):
    return mark_absent(request)