import bcrypt
from .connection import get_connection

# ---------- Password Helpers ----------
def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# ---------- Users ----------
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

def update_student_total_credits(matric):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COALESCE(SUM(c.CreditHours), 0)
                FROM Enrollments e
                JOIN Courses c ON e.CourseCode = c.CourseCode
                WHERE e.StudentID = %s AND e.Grade IN ('A','B','C','D')
            """, (matric,))
            total = cur.fetchone()[0]
            cur.execute("UPDATE Students SET TotalCreditsEarned = %s WHERE MatricNo = %s", (total, matric))
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
def get_all_courses():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT CourseCode, CourseName, DefaultSemester, CreditHours, Cohort, Program, CourseGroup FROM Courses ORDER BY DefaultSemester, CourseCode")
            return cur.fetchall()

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
def get_course_prerequisite(course_code):
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

def delete_prerequisite(id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM Prerequisites WHERE ID = %s", (id,))
            conn.commit()

# ---------- Enrollments ----------
def get_semester_enrollments(semester, advisor_id=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            if advisor_id:
                cur.execute("""
                    SELECT e.ID, e.StudentID, s.Name AS StudentName, e.CourseCode, c.CourseName,
                           e.SemesterSession, e.AttemptType, e.Grade
                    FROM Enrollments e
                    JOIN Students s ON e.StudentID = s.MatricNo
                    JOIN Courses c ON e.CourseCode = c.CourseCode
                    WHERE c.DefaultSemester = %s AND s.AdvisorID = %s
                    ORDER BY s.Name, e.CourseCode
                """, (semester, advisor_id))
            else:
                cur.execute("""
                    SELECT e.ID, e.StudentID, s.Name AS StudentName, e.CourseCode, c.CourseName,
                           e.SemesterSession, e.AttemptType, e.Grade
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
                SELECT ID, StudentID, CourseCode, SemesterSession, AttemptType, Grade
                FROM Enrollments
                WHERE StudentID = %s
                ORDER BY SemesterSession DESC, AttemptType DESC
            """, (student_id,))
            return cur.fetchall()

def get_failed_courses(student_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT CourseCode, AttemptType, Grade
                FROM Enrollments
                WHERE StudentID = %s AND Grade IN ('D', 'F', 'TANGGUH')
                ORDER BY SemesterSession DESC
            """, (student_id,))
            return cur.fetchall()

def add_enrollment(student_id, course_code, semester_session, attempt_type, grade):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO Enrollments (StudentID, CourseCode, SemesterSession, AttemptType, Grade)
                VALUES (%s, %s, %s, %s, %s)
            """, (student_id, course_code.upper(), semester_session, attempt_type, grade))
            conn.commit()

def update_enrollment(id, grade, attempt_type, semester_session):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE Enrollments
                SET Grade = %s, AttemptType = %s, SemesterSession = %s
                WHERE ID = %s
            """, (grade, attempt_type, semester_session, id))
            conn.commit()

def delete_enrollment(id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM Enrollments WHERE ID = %s", (id,))
            conn.commit()

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
    passed_codes = {e[2] for e in enrollments if e[5] in ('A','B','C')}
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