import os
import sys
import io
import tempfile
import csv
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Request, Response, HTTPException, Depends, UploadFile, File, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure project root is in python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from database.connection import get_connection, close_pool
from database.init_db import init_database
from database.models import (
    validate_user, register_user, update_user_password, get_all_users, get_all_advisors,
    get_all_students, get_students_by_advisor, add_student, update_student, delete_student,
    get_student_cgpa, get_student_current_semester, sync_all_students_metrics, compute_student_metrics,
    get_all_courses, add_course, update_course, delete_course, clean_course_code,
    get_distinct_course_cohorts, get_distinct_course_programs, get_cached_courses,
    get_all_prerequisites_batch, get_course_prerequisite, get_prereq_id, add_prerequisite, delete_prerequisite,
    get_semester_enrollments, get_student_enrollments, get_failed_courses, add_enrollment,
    update_enrollment, delete_enrollment, get_max_credits_by_cgpa, get_student_future_courses,
    get_default_session, GRADE_POINTS
)
import database.models
database.models.get_enrollments_for_semester = getattr(database.models, 'get_semester_enrollments', None)
from engine.planner import is_internship_eligible, generate_plan
from utils.importer import (
    parse_file, auto_map_columns, import_courses, import_prerequisites,
    import_students, import_enrollments
)
from web.auth import create_access_token, get_current_user, get_optional_user

# Ensure database tables exist
init_database()

app = FastAPI(title="Politeknik Student Course Management API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- Request Models -----------------
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    ic_number: str
    password: str
    full_name: str
    cohort: Optional[str] = None
    program: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    user_identifier: str
    new_password: str

class StudentCreateRequest(BaseModel):
    matric: str
    name: str
    cgpa: float = 0.0
    class_name: str = ""
    advisor_id: Optional[int] = None
    program: Optional[str] = None
    current_semester: int = 1

class StudentUpdateRequest(BaseModel):
    name: str
    cgpa: float = 0.0
    class_name: str = ""
    advisor_id: Optional[int] = None
    program: Optional[str] = None
    current_semester: int = 1

class CourseCreateRequest(BaseModel):
    code: str
    name: str
    semester: int
    credits: int
    cohort: Optional[str] = None
    program: Optional[str] = None
    course_group: Optional[str] = None
    prerequisites: Optional[List[str]] = None

class CourseUpdateRequest(BaseModel):
    name: str
    semester: int
    credits: int
    cohort: Optional[str] = None
    program: Optional[str] = None
    course_group: Optional[str] = None

class PrereqRequest(BaseModel):
    course_code: str
    prereq_code: str

class EnrollmentCreateRequest(BaseModel):
    student_id: str
    course_code: str
    semester_session: str
    attempt_type: str = "NORMAL"
    grade: Optional[str] = None
    pass_status: Optional[str] = None

class EnrollmentUpdateRequest(BaseModel):
    grade: Optional[str] = None
    attempt_type: str = "NORMAL"
    semester_session: str
    pass_status: Optional[str] = None

# ----------------- Authentication Routes -----------------
@app.post("/api/auth/login")
def login(req: LoginRequest, response: Response):
    user = validate_user(req.username.strip(), req.password.strip())
    if not user:
        raise HTTPException(status_code=401, detail="Invalid IC Number or password.")
    
    token = create_access_token(user)
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=7 * 24 * 3600,
        samesite="lax"
    )
    return {"status": "success", "token": token, "user": user}

@app.post("/api/auth/register")
def register(req: RegisterRequest):
    success = register_user(
        ic_number=req.ic_number.strip(),
        password=req.password.strip(),
        full_name=req.full_name.strip(),
        cohort=req.cohort.strip() if req.cohort else None,
        program=req.program.strip() if req.program else None
    )
    if not success:
        raise HTTPException(status_code=400, detail="Registration failed. IC Number may already be in use.")
    return {"status": "success", "message": "Advisor account registered successfully."}

@app.get("/api/auth/me")
def get_me(user: Dict[str, Any] = Depends(get_current_user)):
    return {"status": "success", "user": user}

@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie(key="session_token")
    return {"status": "success", "message": "Logged out successfully."}

@app.post("/api/auth/change-password")
def change_password(req: ChangePasswordRequest, user: Dict[str, Any] = Depends(get_current_user)):
    is_admin = bool(user.get("role") and str(user["role"]).lower() in ('admin', 'system administrator'))
    if not is_admin and str(user.get("user_id")) != str(req.user_identifier) and str(user.get("username")) != str(req.user_identifier):
        raise HTTPException(status_code=403, detail="Permission denied. Only admins can reset other accounts.")
    
    ok = update_user_password(req.user_identifier, req.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to update password.")
    return {"status": "success", "message": "Password updated successfully."}

@app.get("/api/advisors")
def get_advisors():
    rows = get_all_advisors()
    return [{"id": r[0], "username": r[1], "name": r[2], "program": r[3]} for r in rows]

@app.get("/api/users")
def get_users(user: Dict[str, Any] = Depends(get_current_user)):
    is_admin = bool(user.get("role") and str(user["role"]).lower() in ('admin', 'system administrator'))
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required.")
    rows = get_all_users()
    return [{"id": r[0], "name": r[1], "role": r[2], "username": r[3], "program": r[4]} for r in rows]

# ----------------- Students Routes -----------------
@app.get("/api/students")
def get_students(
    search: Optional[str] = None,
    program: Optional[str] = None,
    advisor_id: Optional[int] = None,
    user: Dict[str, Any] = Depends(get_current_user)
):
    is_admin = bool(user.get("role") and str(user["role"]).lower() in ('admin', 'system administrator'))
    
    # Non-admins default to their assigned students unless specifically searching
    query_advisor = advisor_id
    if not is_admin and query_advisor is None:
        query_advisor = user.get("user_id")

    if query_advisor:
        rows = get_students_by_advisor(query_advisor)
        # Columns: MatricNo, Name, CurrentCGPA, Class, TotalCreditsEarned, CurrentSemesterCredits, Program, CurrentSemester
        student_list = []
        for r in rows:
            student_list.append({
                "matric": r[0],
                "name": r[1],
                "cgpa": float(r[2]) if r[2] is not None else 0.0,
                "class_name": r[3] or "",
                "total_credits": float(r[4]) if r[4] is not None else 0.0,
                "current_sem_credits": float(r[5]) if r[5] is not None else 0.0,
                "advisor_name": user.get("full_name") or "You",
                "advisor_id": query_advisor,
                "program": r[6] or "",
                "current_semester": r[7] if len(r) > 7 and r[7] else 1
            })
    else:
        rows = get_all_students()
        # Columns: s.MatricNo, s.Name, s.CurrentCGPA, s.Class, s.TotalCreditsEarned, s.CurrentSemesterCredits, u.FullName AS AdvisorName, s.Program, s.CurrentSemester
        student_list = []
        for r in rows:
            student_list.append({
                "matric": r[0],
                "name": r[1],
                "cgpa": float(r[2]) if r[2] is not None else 0.0,
                "class_name": r[3] or "",
                "total_credits": float(r[4]) if r[4] is not None else 0.0,
                "current_sem_credits": float(r[5]) if r[5] is not None else 0.0,
                "advisor_name": r[6] or "Unassigned",
                "advisor_id": None,
                "program": r[7] or "",
                "current_semester": r[8] if len(r) > 8 and r[8] else 1
            })

    # Filtering
    if program:
        student_list = [s for s in student_list if str(s["program"]).upper() == str(program).upper()]
    if search:
        s_lower = search.lower()
        student_list = [s for s in student_list if s_lower in s["matric"].lower() or s_lower in s["name"].lower() or s_lower in s["class_name"].lower()]

    return student_list

@app.post("/api/students")
def create_student(req: StudentCreateRequest, user: Dict[str, Any] = Depends(get_current_user)):
    adv_id = req.advisor_id or user.get("user_id")
    try:
        add_student(
            matric=req.matric.strip().upper(),
            name=req.name.strip().upper(),
            cgpa=req.cgpa,
            class_name=req.class_name.strip(),
            advisor_id=adv_id,
            program=req.program.strip().upper() if req.program else None,
            current_semester=req.current_semester
        )
        return {"status": "success", "message": "Student added successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to add student: {str(e)}")

@app.put("/api/students/{matric}")
def edit_student(matric: str, req: StudentUpdateRequest, user: Dict[str, Any] = Depends(get_current_user)):
    try:
        update_student(
            matric=matric.strip().upper(),
            name=req.name.strip().upper(),
            cgpa=req.cgpa,
            class_name=req.class_name.strip(),
            advisor_id=req.advisor_id,
            program=req.program.strip().upper() if req.program else None,
            current_semester=req.current_semester
        )
        return {"status": "success", "message": "Student updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update student: {str(e)}")

@app.delete("/api/students/{matric}")
def remove_student(matric: str, user: Dict[str, Any] = Depends(get_current_user)):
    try:
        delete_student(matric.strip().upper())
        return {"status": "success", "message": "Student deleted."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/students/sync-metrics")
def sync_metrics(user: Dict[str, Any] = Depends(get_current_user)):
    try:
        sync_all_students_metrics()
        return {"status": "success", "message": "All student metrics synchronized successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/students/{matric}/details")
def get_student_detail(matric: str):
    clean_matric = matric.strip().upper()
    cgpa = get_student_cgpa(clean_matric)
    current_sem = get_student_current_semester(clean_matric)
    cgpa_val, total_earned, current_sem_cred = compute_student_metrics(clean_matric)
    internship = is_internship_eligible(clean_matric)
    failed = get_failed_courses(clean_matric)
    enrollments_raw = get_student_enrollments(clean_matric)
    
    # Enrollments formatted
    enrollment_list = []
    courses_cache = get_cached_courses()
    for row in enrollments_raw:
        eid, sid, ccode, session, attempt, grade, pass_status = row
        clean_c = clean_course_code(ccode)
        course_name = courses_cache.get(clean_c, (ccode, ccode, 1, 0, ""))[1]
        cred = courses_cache.get(clean_c, (ccode, ccode, 1, 0, ""))[3]
        enrollment_list.append({
            "id": eid,
            "course_code": ccode,
            "course_name": course_name,
            "credit_hours": cred,
            "semester_session": session,
            "attempt_type": attempt,
            "grade": grade,
            "pass_status": pass_status
        })

    max_credits = get_max_credits_by_cgpa(cgpa)

    return {
        "matric": clean_matric,
        "cgpa": cgpa_val,
        "current_semester": current_sem,
        "total_credits_earned": total_earned,
        "current_semester_credits": current_sem_cred,
        "max_credits_allowed": max_credits,
        "internship_eligible": internship,
        "failed_courses": [{"course_code": f[0], "attempt_type": f[1], "grade": f[2], "pass_status": f[3]} for f in failed],
        "enrollments": enrollment_list
    }

# ----------------- Courses & Prerequisites Routes -----------------
@app.get("/api/courses")
def get_courses(
    cohort: Optional[str] = None,
    program: Optional[str] = None,
    semester: Optional[int] = None,
    search: Optional[str] = None
):
    rows = get_all_courses()
    prereq_batch = get_all_prerequisites_batch()
    
    courses = []
    for r in rows:
        code, name, sem, credits, c_cohort, c_prog, c_group = r
        clean_c = clean_course_code(code)
        prereqs = prereq_batch.get(clean_c, [])
        courses.append({
            "course_code": code,
            "course_name": name,
            "default_semester": sem,
            "credit_hours": credits,
            "cohort": c_cohort or "",
            "program": c_prog or "",
            "course_group": c_group or "",
            "prerequisites": prereqs
        })

    if cohort:
        courses = [c for c in courses if c["cohort"].upper() == cohort.upper()]
    if program:
        courses = [c for c in courses if c["program"].upper() == program.upper()]
    if semester:
        courses = [c for c in courses if c["default_semester"] == semester]
    if search:
        s_lower = search.lower()
        courses = [c for c in courses if s_lower in c["course_code"].lower() or s_lower in c["course_name"].lower()]

    return courses

@app.post("/api/courses")
def create_course(req: CourseCreateRequest, user: Dict[str, Any] = Depends(get_current_user)):
    try:
        final_code = add_course(
            code=req.code.strip(),
            name=req.name.strip(),
            semester=req.semester,
            credits=req.credits,
            cohort=req.cohort.strip() if req.cohort else None,
            program=req.program.strip() if req.program else None,
            course_group=req.course_group.strip() if req.course_group else None
        )
        if req.prerequisites:
            for p in req.prerequisites:
                if p and p.strip():
                    try:
                        add_prerequisite(final_code, p.strip().upper())
                    except Exception:
                        pass
        return {"status": "success", "course_code": final_code, "message": f"Course {final_code} added successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/courses/{code}")
def edit_course(code: str, req: CourseUpdateRequest, user: Dict[str, Any] = Depends(get_current_user)):
    try:
        update_course(
            code=code.strip().upper(),
            name=req.name.strip(),
            semester=req.semester,
            credits=req.credits,
            cohort=req.cohort.strip() if req.cohort else None,
            program=req.program.strip() if req.program else None,
            course_group=req.course_group.strip() if req.course_group else None
        )
        return {"status": "success", "message": f"Course {code} updated."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/courses/{code}")
def remove_course(code: str, user: Dict[str, Any] = Depends(get_current_user)):
    try:
        delete_course(code.strip().upper())
        return {"status": "success", "message": f"Course {code} deleted."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/courses/cohorts")
def list_cohorts():
    return get_distinct_course_cohorts()

@app.get("/api/courses/programs")
def list_programs():
    return get_distinct_course_programs()

@app.get("/api/prerequisites")
def list_prerequisites():
    return get_all_prerequisites_batch()

@app.post("/api/prerequisites")
def create_prerequisite(req: PrereqRequest, user: Dict[str, Any] = Depends(get_current_user)):
    try:
        add_prerequisite(req.course_code.strip().upper(), req.prereq_code.strip().upper())
        return {"status": "success", "message": "Prerequisite added."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/prerequisites")
def remove_prerequisite(course_code: str, prereq_code: str, user: Dict[str, Any] = Depends(get_current_user)):
    pid = get_prereq_id(course_code.strip(), prereq_code.strip())
    if not pid:
        raise HTTPException(status_code=404, detail="Prerequisite relation not found.")
    delete_prerequisite(pid)
    return {"status": "success", "message": "Prerequisite removed."}

# ----------------- Enrollments Routes -----------------
@app.get("/api/enrollments")
def get_enrollments(
    student_id: Optional[str] = None,
    semester: Optional[int] = None,
    user: Dict[str, Any] = Depends(get_current_user)
):
    if student_id:
        clean_sid = student_id.strip().upper()
        rows = get_student_enrollments(clean_sid)
        courses_cache = get_cached_courses()
        results = []
        for r in rows:
            eid, sid, ccode, session, attempt, grade, pass_status = r
            clean_c = clean_course_code(ccode)
            course_name = courses_cache.get(clean_c, (ccode, ccode, 1, 0, ""))[1]
            cred = courses_cache.get(clean_c, (ccode, ccode, 1, 0, ""))[3]
            results.append({
                "id": eid,
                "student_id": sid,
                "course_code": ccode,
                "course_name": course_name,
                "credit_hours": cred,
                "semester_session": session,
                "attempt_type": attempt,
                "grade": grade or "",
                "pass_status": pass_status or "Dalam Progres"
            })
        return results

    if semester:
        is_admin = bool(user.get("role") and str(user["role"]).lower() in ('admin', 'system administrator'))
        advisor_filter = None if is_admin else user.get("user_id")
        rows = get_semester_enrollments(semester, advisor_id=advisor_filter)
        results = []
        for r in rows:
            eid, sid, sname, ccode, cname, session, attempt, grade, pass_status = r
            results.append({
                "id": eid,
                "student_id": sid,
                "student_name": sname,
                "course_code": ccode,
                "course_name": cname,
                "semester_session": session,
                "attempt_type": attempt,
                "grade": grade or "",
                "pass_status": pass_status or "Dalam Progres"
            })
        return results

    return []

@app.post("/api/enrollments")
def create_enrollment(req: EnrollmentCreateRequest, user: Dict[str, Any] = Depends(get_current_user)):
    try:
        add_enrollment(
            student_id=req.student_id.strip().upper(),
            course_code=req.course_code.strip().upper(),
            semester_session=req.semester_session.strip(),
            attempt_type=req.attempt_type.strip(),
            grade=req.grade.strip() if req.grade else None,
            pass_status=req.pass_status.strip() if req.pass_status else None
        )
        return {"status": "success", "message": "Enrollment recorded successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/enrollments/{enrollment_id}")
def edit_enrollment(enrollment_id: int, req: EnrollmentUpdateRequest, user: Dict[str, Any] = Depends(get_current_user)):
    try:
        update_enrollment(
            id=enrollment_id,
            grade=req.grade.strip() if req.grade else None,
            attempt_type=req.attempt_type.strip(),
            semester_session=req.semester_session.strip(),
            pass_status=req.pass_status.strip() if req.pass_status else None
        )
        return {"status": "success", "message": "Enrollment updated."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/enrollments/{enrollment_id}")
def remove_enrollment(enrollment_id: int, user: Dict[str, Any] = Depends(get_current_user)):
    try:
        delete_enrollment(enrollment_id)
        return {"status": "success", "message": "Enrollment deleted."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ----------------- Academic Planner Routes -----------------
@app.get("/api/planner/{student_id}")
def get_planner(student_id: str):
    clean_sid = student_id.strip().upper()
    current_sem = get_student_current_semester(clean_sid)
    cgpa = get_student_cgpa(clean_sid)
    max_credits = get_max_credits_by_cgpa(cgpa)
    internship = is_internship_eligible(clean_sid)
    
    # Future recommendations
    future_data = get_student_future_courses(clean_sid, current_sem)
    
    # Failed courses that must be retaken
    failed_rows = get_failed_courses(clean_sid)
    courses_cache = get_cached_courses()
    retakes = []
    for f in failed_rows:
        ccode, attempt, grade, pass_status = f
        clean_c = clean_course_code(ccode)
        c_info = courses_cache.get(clean_c, (ccode, ccode, 1, 0, ""))
        retakes.append({
            "course_code": ccode,
            "course_name": c_info[1],
            "credit_hours": c_info[3],
            "default_semester": c_info[2],
            "last_grade": grade,
            "last_attempt": attempt
        })

    # Target plan for next semester
    next_sem = current_sem + 1 if current_sem < 6 else 6
    target_plan = generate_plan(clean_sid, next_sem)

    return {
        "student_id": clean_sid,
        "current_semester": current_sem,
        "next_semester": next_sem,
        "cgpa": cgpa,
        "max_credits": max_credits,
        "internship_eligible": internship,
        "retakes_needed": retakes,
        "future_recommended_courses": future_data["recommended"],
        "recommended_total_credits": future_data["total_credits"],
        "generated_target_plan": target_plan
    }

# ----------------- Import & Export Routes -----------------
@app.post("/api/import")
async def import_file(
    file: UploadFile = File(...),
    import_type: str = Form("All"),
    sheet_name: Optional[str] = Form(None),
    user: Dict[str, Any] = Depends(get_current_user)
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.csv', '.txt', '.xlsx', '.xls', '.pdf']:
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload CSV, Excel, or PDF.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        df = parse_file(tmp_path, sheet_name=sheet_name)
        mapping = auto_map_columns(df.columns, import_type)
        df_mapped = df.rename(columns={v: k for k, v in mapping.items()})

        counts = {
            "courses": 0,
            "prerequisites": 0,
            "students": 0,
            "enrollments": 0
        }

        if import_type in ['All', 'Courses']:
            if 'CourseCode' in df_mapped.columns and 'CourseName' in df_mapped.columns:
                counts["courses"] = import_courses(df_mapped, ['CourseCode', 'CourseName'])
        
        if import_type in ['All', 'Prerequisites']:
            if 'CourseCode' in df_mapped.columns and 'PrereqCode' in df_mapped.columns:
                counts["prerequisites"] = import_prerequisites(df_mapped, ['CourseCode', 'PrereqCode'])

        if import_type in ['All', 'Students']:
            if 'MatricNo' in df_mapped.columns and 'Name' in df_mapped.columns:
                counts["students"] = import_students(df_mapped, ['MatricNo', 'Name'])

        if import_type in ['All', 'Enrollments']:
            if 'StudentID' in df_mapped.columns and 'CourseCode' in df_mapped.columns:
                counts["enrollments"] = import_enrollments(df_mapped, ['StudentID', 'CourseCode'])

        sync_all_students_metrics()

        return {
            "status": "success",
            "message": f"Import completed: {counts['students']} students, {counts['courses']} courses, {counts['enrollments']} enrollments.",
            "counts": counts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

@app.get("/api/export/csv")
def export_csv(user: Dict[str, Any] = Depends(get_current_user)):
    rows = get_all_students()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["MatricNo", "Name", "Class", "CurrentCGPA", "TotalCreditsEarned", "CurrentSemesterCredits", "Advisor", "Program", "CurrentSemester"])
    for r in rows:
        writer.writerow([r[0], r[1], r[3] or "", f"{r[2]:.2f}" if r[2] else "0.00", f"{r[4]:.1f}" if r[4] else "0.0", f"{r[5]:.1f}" if r[5] else "0.0", r[6] or "", r[7] or "", r[8] or 1])
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=politeknik_students_records.csv"}
    )

@app.get("/api/export/xlsx")
def export_xlsx(user: Dict[str, Any] = Depends(get_current_user)):
    rows = get_all_students()
    headers = ["MatricNo", "Name", "Class", "CurrentCGPA", "TotalCreditsEarned", "CurrentSemesterCredits", "Advisor", "Program", "CurrentSemester"]
    content = [
        '<?xml version="1.0"?>',
        '<?mso-application progid="Excel.Sheet"?>',
        '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">',
        '<Worksheet ss:Name="Students"><Table>',
        '<Row>' + ''.join(f'<Cell><Data ss:Type="String">{h}</Data></Cell>' for h in headers) + '</Row>'
    ]
    for r in rows:
        cells = [
            f'<Cell><Data ss:Type="String">{r[0]}</Data></Cell>',
            f'<Cell><Data ss:Type="String">{r[1]}</Data></Cell>',
            f'<Cell><Data ss:Type="String">{r[3] or ""}</Data></Cell>',
            f'<Cell><Data ss:Type="Number">{r[2] if r[2] is not None else 0.0}</Data></Cell>',
            f'<Cell><Data ss:Type="Number">{r[4] if r[4] is not None else 0.0}</Data></Cell>',
            f'<Cell><Data ss:Type="Number">{r[5] if r[5] is not None else 0.0}</Data></Cell>',
            f'<Cell><Data ss:Type="String">{r[6] or ""}</Data></Cell>',
            f'<Cell><Data ss:Type="String">{r[7] or ""}</Data></Cell>',
            f'<Cell><Data ss:Type="Number">{r[8] if len(r)>8 and r[8] else 1}</Data></Cell>',
        ]
        content.append('<Row>' + ''.join(cells) + '</Row>')
    content.append('</Table></Worksheet></Workbook>')
    xml_str = '\n'.join(content)
    return StreamingResponse(
        io.BytesIO(xml_str.encode('utf-8')),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=politeknik_students_records.xls"}
    )

# ----------------- Static Frontend Mount -----------------
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return HTMLResponse("<h1>Politeknik Course Management API</h1><p>Frontend static files not found.</p>")

@app.on_event("shutdown")
def on_shutdown():
    close_pool()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.server:app", host="0.0.0.0", port=8000, reload=True)
