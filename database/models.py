import bcrypt
import re
from .connection import get_connection

# ---------- Grade Points ----------
GRADE_POINTS = {
    'A+': 4.00,
    'A': 4.00,
    'A-': 3.67,
    'B+': 3.33,
    'B': 3.00,
    'B-': 2.67,
    'C+': 2.33,
    'C': 2.00,
    'C-': 1.67,
    'D+': 1.33,
    'D': 1.00,
    'E': 0.67,      # GAGAL
    'E-': 0.33,     # GAGAL
    'F': 0.00,      # GAGAL
    'TANGGUH': None,
}

# ---------- Course Credit & Semester Helpers ----------
def get_course_credit_hours(course_code, courses_cache=None):
    if not course_code:
        return 0
    clean_c = clean_course_code(course_code)
    if courses_cache and clean_c in courses_cache:
        cred = courses_cache[clean_c][3]
        if cred and cred > 0:
            return cred
    match = re.search(r'(\d)(?:-[0-9]+)?$', str(course_code).strip())
    if match:
        return int(match.group(1))
    return 0

def get_semester_number_from_session(session_str):
    if not session_str:
        return None
    s_str = str(session_str).strip()
    match = re.search(r'(?:SEM|SEMESTER)\s*([1-8])\b', s_str, re.IGNORECASE)
    if match:
        return int(match.group(1))
    match_sesi = re.search(r'SESI\s*([1-8])\b', s_str, re.IGNORECASE)
    if match_sesi:
        return int(match_sesi.group(1))
    match_num = re.search(r'(?<!\d)([1-8])(?!\d)', s_str)
    if match_num:
        return int(match_num.group(1))
    return None

def get_default_session(advisor_id, semester):
    if advisor_id:
        cohort = get_user_cohort(advisor_id)
        if cohort:
            return f"{cohort}-SEM{semester}"
    return f"2025/2026-SEM{semester}"

# ---------- Course Cache ----------
_COURSE_CACHE = None

def get_cached_courses():
    global _COURSE_CACHE
    if _COURSE_CACHE is None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT CourseCode, CourseName, DefaultSemester, CreditHours, CourseGroup FROM Courses")
                rows = cur.fetchall()
                cache = {}
                for r in rows:
                    raw_code, name, sem, cred, grp = r
                    clean_c = clean_course_code(raw_code)
                    cache[clean_c] = (raw_code, name, sem, cred, grp)
                _COURSE_CACHE = cache
    return _COURSE_CACHE

# ---------- Student Metrics Calculation (CGPA, Total Credits, Semester Credits) ----------
def compute_student_metrics(student_id):
    current_sem = get_student_current_semester(student_id)
    courses_cache = get_cached_courses()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT e.CourseCode, e.Grade, e.PassStatus, e.SemesterSession, c.CreditHours, c.DefaultSemester
                FROM Enrollments e
                LEFT JOIN Courses c ON e.CourseCode = c.CourseCode
                WHERE e.StudentID = %s
                ORDER BY e.ID ASC
            """, (student_id,))
            rows = cur.fetchall()

    latest_course_grades = {}
    passed_courses = {}
    current_sem_credits = 0

    for raw_code, grade, pass_status, session, db_cred, def_sem in rows:
        clean_code = clean_course_code(raw_code)
        cred = db_cred if (db_cred and db_cred > 0) else get_course_credit_hours(raw_code, courses_cache)

        grade_str = str(grade).strip().upper() if grade else ""
        pass_str = str(pass_status).strip().upper() if pass_status else ""

        if grade_str == 'TANGGUH' or pass_str == 'TANGGUH' or grade_str == 'IN PROGRESS':
            pass
        else:
            gp = None
            if pass_str == 'GAGAL' or grade_str in ('E', 'E-', 'F', 'GAGAL'):
                if grade_str == 'E':
                    gp = 0.67
                elif grade_str == 'E-':
                    gp = 0.33
                else:
                    gp = 0.00
            elif grade_str in GRADE_POINTS:
                gp = GRADE_POINTS[grade_str]

            if gp is not None and cred > 0:
                latest_course_grades[clean_code] = (gp, cred)

            if (pass_str == 'LULUS' or (gp is not None and gp >= 1.00 and pass_str != 'GAGAL')) and cred > 0:
                passed_courses[clean_code] = cred

        sem_num = get_semester_number_from_session(session)
        if sem_num is None and def_sem is not None:
            sem_num = def_sem

        if sem_num == current_sem and cred > 0:
            current_sem_credits += cred

    total_points = sum(gp * c for gp, c in latest_course_grades.values())
    total_credits = sum(c for gp, c in latest_course_grades.values())
    cgpa = round(total_points / total_credits, 2) if total_credits > 0 else 0.0
    total_earned = sum(passed_courses.values())

    return cgpa, total_earned, current_sem_credits

def compute_gpa(student_id):
    cgpa, _, _ = compute_student_metrics(student_id)
    return cgpa

def update_student_cgpa(student_id):
    cgpa, total_earned, current_sem_credits = compute_student_metrics(student_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE Students
                SET CurrentCGPA = %s, TotalCreditsEarned = %s, CurrentSemesterCredits = %s
                WHERE MatricNo = %s
            """, (cgpa, total_earned, current_sem_credits, student_id))
            conn.commit()
    return cgpa

def update_student_current_semester_credits(student_id):
    cgpa, total_earned, current_sem_credits = compute_student_metrics(student_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE Students
                SET CurrentCGPA = %s, TotalCreditsEarned = %s, CurrentSemesterCredits = %s
                WHERE MatricNo = %s
            """, (cgpa, total_earned, current_sem_credits, student_id))
            conn.commit()
    return current_sem_credits

def update_student_total_credits(student_id):
    cgpa, total_earned, current_sem_credits = compute_student_metrics(student_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE Students
                SET CurrentCGPA = %s, TotalCreditsEarned = %s, CurrentSemesterCredits = %s
                WHERE MatricNo = %s
            """, (cgpa, total_earned, current_sem_credits, student_id))
            conn.commit()
    return total_earned

# ---------- Password Helpers ----------
def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# ---------- Users ----------
def update_user_password(user_identifier, new_password):
    hashed = hash_password(new_password)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE Users SET Password = %s
                WHERE UserID = %s OR Username = %s
            """, (hashed, str(user_identifier), str(user_identifier)))
            conn.commit()
    return True

def get_all_users():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT UserID, FullName, Role, Username, Program FROM Users ORDER BY Role, FullName")
            return cur.fetchall()

def register_user(ic_number, password, full_name, cohort, program):
    hashed = hash_password(password)
    cohort = cohort.upper() if cohort else None
    program = program.upper() if program else None
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO Users (Username, Password, Role, FullName, Cohort, Program) VALUES (%s, %s, 'Academic Advisor', %s, %s, %s)",
                    (ic_number, hashed, full_name.upper(), cohort, program)
                )
                conn.commit()
                return True
            except Exception:
                return False

def validate_user(username, password):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT UserID, Password, Role, FullName, Cohort, Program FROM Users WHERE Username = %s",
                (username,)
            )
            row = cur.fetchone()
            if row and check_password(password, row[1]):
                return {
                    'user_id': row[0],
                    'role': row[2] if row[2] else 'Academic Advisor',
                    'full_name': row[3],
                    'cohort': row[4],
                    'program': row[5]
                }
            return None

def get_all_advisors():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT UserID, Username, FullName, Program FROM Users WHERE Role = 'Academic Advisor' ORDER BY FullName")
            return cur.fetchall()

def get_user_cohort(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT Cohort FROM Users WHERE UserID = %s", (user_id,))
            row = cur.fetchone()
            return row[0] if row else None

def get_user_program(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT Program FROM Users WHERE UserID = %s", (user_id,))
            row = cur.fetchone()
            return row[0] if row else None

# ---------- Students ----------
def sync_all_students_metrics():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT MatricNo FROM Students")
                mno_rows = cur.fetchall()
                if not mno_rows:
                    return
                students = [row[0] for row in mno_rows]

            update_params = []
            for student_id in students:
                cgpa, total_earned, current_sem_credits = compute_student_metrics(student_id)
                update_params.append((cgpa, total_earned, current_sem_credits, student_id))

            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.executemany("""
                        UPDATE Students
                        SET CurrentCGPA = %s, TotalCreditsEarned = %s, CurrentSemesterCredits = %s
                        WHERE MatricNo = %s
                    """, update_params)
                    conn.commit()
    except Exception as e:
        print(f"Error in sync_all_students_metrics: {e}")

def get_all_students():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.MatricNo, s.Name, s.CurrentCGPA, s.Class,
                       s.TotalCreditsEarned, s.CurrentSemesterCredits,
                       u.FullName AS AdvisorName, s.Program, s.CurrentSemester
                FROM Students s
                LEFT JOIN Users u ON s.AdvisorID = u.UserID
                ORDER BY s.Name
            """)
            return cur.fetchall()

def get_students_by_advisor(advisor_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT MatricNo, Name, CurrentCGPA, Class,
                       TotalCreditsEarned, CurrentSemesterCredits, Program, CurrentSemester
                FROM Students
                WHERE AdvisorID = %s
                ORDER BY Name
            """, (advisor_id,))
            return cur.fetchall()

def add_student(matric, name, cgpa, class_name, advisor_id, program=None, current_semester=1):
    if program:
        program = program.upper()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO Students (MatricNo, Name, CurrentCGPA, Class, AdvisorID, Program, CurrentSemester) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (matric, name, cgpa, class_name, advisor_id, program, current_semester)
            )
            conn.commit()

def update_student(matric, name, cgpa, class_name, advisor_id, program=None, current_semester=None):
    if program:
        program = program.upper()
    with get_connection() as conn:
        with conn.cursor() as cur:
            if current_semester is not None:
                cur.execute(
                    "UPDATE Students SET Name = %s, CurrentCGPA = %s, Class = %s, AdvisorID = %s, Program = %s, CurrentSemester = %s WHERE MatricNo = %s",
                    (name, cgpa, class_name, advisor_id, program, current_semester, matric)
                )
            else:
                cur.execute(
                    "UPDATE Students SET Name = %s, CurrentCGPA = %s, Class = %s, AdvisorID = %s, Program = %s WHERE MatricNo = %s",
                    (name, cgpa, class_name, advisor_id, program, matric)
                )
            conn.commit()

def delete_student(matric):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM Students WHERE MatricNo = %s", (matric,))
            conn.commit()

def get_student_cgpa(student_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT CurrentCGPA FROM Students WHERE MatricNo = %s", (student_id,))
            row = cur.fetchone()
            return row[0] if row else 0.0

def get_student_current_semester(student_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT CurrentSemester FROM Students WHERE MatricNo = %s", (student_id,))
            row = cur.fetchone()
            return row[0] if row else 1

# ---------- Courses ----------
_EXACT_COURSE_CODES = None

def get_all_exact_course_codes():
    global _EXACT_COURSE_CODES
    if _EXACT_COURSE_CODES is None:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT UPPER(CourseCode) FROM Courses")
                    _EXACT_COURSE_CODES = {row[0] for row in cur.fetchall()}
        except Exception:
            _EXACT_COURSE_CODES = set()
    return _EXACT_COURSE_CODES

def clean_course_code(code):
    if not code:
        return ""
    code_upper = str(code).strip().upper()
    exact_codes = get_all_exact_course_codes()
    if code_upper in exact_codes:
        return code_upper
    import re
    return re.sub(r'-\d+$', '', code_upper)

def get_all_courses():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT CourseCode, CourseName, DefaultSemester, CreditHours, Cohort, Program, CourseGroup FROM Courses ORDER BY DefaultSemester, CourseCode")
            return cur.fetchall()

def get_distinct_course_cohorts():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT Cohort FROM Courses WHERE Cohort IS NOT NULL AND Cohort != '' ORDER BY Cohort")
            return [row[0] for row in cur.fetchall()]

def get_distinct_course_programs():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT Program FROM Courses WHERE Program IS NOT NULL AND Program != '' ORDER BY Program")
            return [row[0] for row in cur.fetchall()]

def is_placeholder_code(code):
    return 'XX' in code or 'XXXXXX' in code or code.endswith('X')

def add_course(code, name, semester, credits, cohort=None, program=None, course_group=None):
    original_code = code.upper()
    final_code = original_code
    if is_placeholder_code(original_code):
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT CourseCode FROM Courses WHERE CourseCode LIKE %s", (original_code + '%',))
                existing = [row[0] for row in cur.fetchall()]
                if original_code in existing:
                    max_num = 0
                    for ec in existing:
                        if ec == original_code:
                            max_num = max(max_num, 0)
                        elif ec.startswith(original_code + '-'):
                            try:
                                num = int(ec.split('-')[-1])
                                max_num = max(max_num, num)
                            except:
                                pass
                    final_code = f"{original_code}-{max_num+1}"
    if cohort:
        cohort = cohort.upper()
    if program:
        program = program.upper()
    if course_group:
        course_group = course_group.upper()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO Courses (CourseCode, CourseName, DefaultSemester, CreditHours, Cohort, Program, CourseGroup) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (final_code, name, semester, credits, cohort, program, course_group)
            )
            conn.commit()
    return final_code

def update_course(code, name, semester, credits, cohort=None, program=None, course_group=None):
    if cohort:
        cohort = cohort.upper()
    if program:
        program = program.upper()
    if course_group:
        course_group = course_group.upper()
    with get_connection() as conn:
        with conn.cursor() as cur:
            set_parts = ["CourseName = %s", "DefaultSemester = %s", "CreditHours = %s"]
            params = [name, semester, credits]
            if cohort is not None:
                set_parts.append("Cohort = %s")
                params.append(cohort)
            if program is not None:
                set_parts.append("Program = %s")
                params.append(program)
            if course_group is not None:
                set_parts.append("CourseGroup = %s")
                params.append(course_group)
            params.append(code.upper())
            sql = f"UPDATE Courses SET {', '.join(set_parts)} WHERE CourseCode = %s"
            cur.execute(sql, tuple(params))
            conn.commit()

def delete_course(code):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM Courses WHERE CourseCode = %s", (code.upper(),))
            conn.commit()

# ---------- Prerequisites ----------
_PREREQ_CACHE = None

def get_all_prerequisites_batch(force_refresh=False):
    global _PREREQ_CACHE
    if _PREREQ_CACHE is None or force_refresh:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT CourseCode, PrereqCode FROM Prerequisites ORDER BY CourseCode, PrereqCode")
                    cache = {}
                    for c_code, p_code in cur.fetchall():
                        clean_c = clean_course_code(c_code)
                        if clean_c not in cache:
                            cache[clean_c] = []
                        cache[clean_c].append(p_code)
                    _PREREQ_CACHE = cache
        except Exception:
            _PREREQ_CACHE = {}
    return _PREREQ_CACHE

def get_course_prerequisite(course_code):
    batch = get_all_prerequisites_batch()
    clean_c = clean_course_code(course_code)
    if clean_c in batch:
        return batch[clean_c]
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT PrereqCode FROM Prerequisites WHERE CourseCode = %s ORDER BY PrereqCode", (course_code.upper(),))
            return [row[0] for row in cur.fetchall()]

def get_prereq_id(course_code, prereq_code):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT ID FROM Prerequisites WHERE CourseCode = %s AND PrereqCode = %s", (course_code.upper(), prereq_code.upper(),))
            row = cur.fetchone()
            return row[0] if row else None

def add_prerequisite(course, prereq):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO Prerequisites (CourseCode, PrereqCode) VALUES (%s, %s)",
                (course.upper(), prereq.upper())
            )
            conn.commit()
    get_all_prerequisites_batch(force_refresh=True)

def delete_prerequisite(id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM Prerequisites WHERE ID = %s", (id,))
            conn.commit()
    get_all_prerequisites_batch(force_refresh=True)

# ---------- Enrollments ----------
def get_semester_enrollments(semester, advisor_id=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            if advisor_id:
                cur.execute("""
                    SELECT e.ID, e.StudentID, s.Name AS StudentName, e.CourseCode, c.CourseName,
                           e.SemesterSession, e.AttemptType, e.Grade, e.PassStatus
                    FROM Enrollments e
                    JOIN Students s ON e.StudentID = s.MatricNo
                    JOIN Courses c ON e.CourseCode = c.CourseCode
                    WHERE c.DefaultSemester = %s AND s.AdvisorID = %s
                    ORDER BY s.Name, e.CourseCode
                """, (semester, advisor_id))
            else:
                cur.execute("""
                    SELECT e.ID, e.StudentID, s.Name AS StudentName, e.CourseCode, c.CourseName,
                           e.SemesterSession, e.AttemptType, e.Grade, e.PassStatus
                    FROM Enrollments e
                    JOIN Students s ON e.StudentID = s.MatricNo
                    JOIN Courses c ON e.CourseCode = c.CourseCode
                    WHERE c.DefaultSemester = %s
                    ORDER BY s.Name, e.CourseCode
                """, (semester,))
            return cur.fetchall()

def get_student_enrollments(student_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ID, StudentID, CourseCode, SemesterSession, AttemptType, Grade, PassStatus
                FROM Enrollments
                WHERE StudentID = %s
                ORDER BY SemesterSession DESC, AttemptType DESC
            """, (student_id,))
            return cur.fetchall()

def get_failed_courses(student_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT CourseCode, AttemptType, Grade, PassStatus
                FROM Enrollments
                WHERE StudentID = %s AND PassStatus = 'GAGAL'
                ORDER BY SemesterSession DESC
            """, (student_id,))
            return cur.fetchall()

def _determine_pass_status(grade):
    """Return 'GAGAL' for fail grades, 'TANGGUH' for TANGGUH, 'LULUS' for passing grades, else None for In Progress."""
    if grade in ('E', 'E-', 'F'):
        return 'GAGAL'
    elif grade == 'TANGGUH':
        return 'TANGGUH'
    elif grade is not None and grade != '' and grade != 'In Progress':
        return 'LULUS'
    return None

def add_enrollment(student_id, course_code, semester_session, attempt_type, grade, pass_status=None):
    # Auto-set pass_status based on grade if not explicitly provided
    if grade in ('E', 'E-', 'F'):
        pass_status = 'GAGAL'
    elif grade == 'TANGGUH':
        pass_status = 'TANGGUH'
    elif not pass_status and grade is not None and grade != '' and grade != 'In Progress':
        pass_status = _determine_pass_status(grade)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO Enrollments (StudentID, CourseCode, SemesterSession, AttemptType, Grade, PassStatus)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (student_id, course_code.upper(), semester_session, attempt_type, grade, pass_status))
            conn.commit()
    update_student_cgpa(student_id)
    update_student_total_credits(student_id)
    update_student_current_semester_credits(student_id)

def update_enrollment(id, grade, attempt_type, semester_session, pass_status=None):
    if grade in ('E', 'E-', 'F'):
        pass_status = 'GAGAL'
    elif grade == 'TANGGUH':
        pass_status = 'TANGGUH'
    elif not pass_status and grade is not None and grade != '' and grade != 'In Progress':
        pass_status = _determine_pass_status(grade)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT StudentID FROM Enrollments WHERE ID = %s", (id,))
            row = cur.fetchone()
            student_id = row[0] if row else None
    if not student_id:
        return
    with get_connection() as conn:
        with conn.cursor() as cur:
            if pass_status is not None:
                cur.execute("""
                    UPDATE Enrollments
                    SET Grade = %s, AttemptType = %s, SemesterSession = %s, PassStatus = %s
                    WHERE ID = %s
                """, (grade, attempt_type, semester_session, pass_status, id))
            else:
                cur.execute("""
                    UPDATE Enrollments
                    SET Grade = %s, AttemptType = %s, SemesterSession = %s
                    WHERE ID = %s
                """, (grade, attempt_type, semester_session, id))
            conn.commit()
    update_student_cgpa(student_id)
    update_student_total_credits(student_id)
    update_student_current_semester_credits(student_id)

def delete_enrollment(id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT StudentID FROM Enrollments WHERE ID = %s", (id,))
            row = cur.fetchone()
            student_id = row[0] if row else None
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM Enrollments WHERE ID = %s", (id,))
            conn.commit()
    if student_id:
        update_student_cgpa(student_id)
        update_student_total_credits(student_id)
        update_student_current_semester_credits(student_id)

def get_students_by_advisor_for_dropdown(advisor_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT MatricNo, Name FROM Students WHERE AdvisorID = %s ORDER BY Name", (advisor_id,))
            return cur.fetchall()

# ---------- Recommendations ----------
def get_max_credits_by_cgpa(cgpa):
    if cgpa >= 2.5:
        return 18
    elif cgpa >= 2.2:
        return 15
    else:
        return 12

def get_student_future_courses(student_id, current_semester):
    cgpa = get_student_cgpa(student_id)
    max_credits = get_max_credits_by_cgpa(cgpa)

    failed = get_failed_courses(student_id)
    failed_codes = {f[0] for f in failed}

    enrollments = get_student_enrollments(student_id)
    passed_codes = {e[2] for e in enrollments if e[6] == 'LULUS'}
    taken_codes = {e[2] for e in enrollments}

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT CourseCode, CourseName, DefaultSemester, CreditHours, Cohort, Program, CourseGroup
                FROM Courses
                WHERE DefaultSemester > %s
                ORDER BY DefaultSemester, CourseCode
            """, (current_semester,))
            future_courses = cur.fetchall()

            course_codes = [row[0] for row in future_courses]
            if course_codes:
                cur.execute("""
                    SELECT CourseCode, PrereqCode
                    FROM Prerequisites
                    WHERE CourseCode = ANY(%s)
                    ORDER BY CourseCode, PrereqCode
                """, (course_codes,))
                prereq_rows = cur.fetchall()
            else:
                prereq_rows = []

        prereq_map = {}
        for ccode, pcode in prereq_rows:
            if ccode not in prereq_map:
                prereq_map[ccode] = []
            prereq_map[ccode].append(pcode)

    recommended = []
    total_credits = 0

    for course in future_courses:
        code, name, sem, cred, cohort, prog, group = course
        if code in passed_codes:
            continue
        is_dropped = code in failed_codes
        prereqs = prereq_map.get(code, [])
        prereqs_satisfied = True
        for p in prereqs:
            if p in passed_codes:
                continue
            if p in failed_codes:
                is_dropped = True
            else:
                if p not in taken_codes:
                    prereqs_satisfied = False
                    break
        if code in failed_codes:
            is_dropped = True
            prereqs_satisfied = True
        if prereqs_satisfied or is_dropped:
            recommended.append({
                'code': code,
                'name': name,
                'semester': sem,
                'credits': cred,
                'is_dropped': is_dropped,
                'prereqs_satisfied': prereqs_satisfied,
                'cohort': cohort,
                'program': prog,
                'course_group': group
            })
            total_credits += cred

    recommended.sort(key=lambda x: (not x['is_dropped'], x['semester']))

    return {
        'recommended': recommended,
        'total_credits': total_credits,
        'max_credits': max_credits
    }