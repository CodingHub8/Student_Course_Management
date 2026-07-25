from database.models import get_enrollments_for_semester
from database.connection import get_connection

def is_internship_eligible(student_id):
    # Assume minimum total credits for internship = 90 (adjust as needed)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT TotalCreditsEarned FROM Students WHERE MatricNo = %s", (student_id,))
            total = cur.fetchone()[0] or 0
            return total >= 90

def get_cgpa(student_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT CurrentCGPA FROM Students WHERE MatricNo = %s", (student_id,))
            row = cur.fetchone()
            return row[0] if row else 0.0

def get_failed_courses(student_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT CourseCode FROM Enrollments
                WHERE StudentID = %s AND Grade IN ('F', 'D', 'TANGGUH')
            """, (student_id,))
            return [row[0] for row in cur.fetchall()]

def check_prereq_status(student_id, course_code):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT PrereqCode FROM Prerequisites WHERE CourseCode = %s", (course_code,))
            prereqs = [row[0] for row in cur.fetchall()]
            if not prereqs:
                return True
            for prereq in prereqs:
                cur.execute("""
                    SELECT 1 FROM Enrollments
                    WHERE StudentID = %s AND CourseCode = %s AND Grade IN ('A','B','C')
                """, (student_id, prereq))
                if not cur.fetchone():
                    return False
            return True

def generate_plan(student_id, target_semester):
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Official courses for this semester
            cur.execute("SELECT CourseCode FROM Courses WHERE DefaultSemester = %s", (target_semester,))
            official = [row[0] for row in cur.fetchall()]

            # Retakes from previous semesters
            retakes = get_failed_courses(student_id)

            # Check prerequisites for all potential courses
            all_courses = list(set(official + retakes))
            blocked = []
            for course in all_courses:
                if not check_prereq_status(student_id, course):
                    blocked.append(course)

            final = [c for c in all_courses if c not in blocked]

            # Compute total credits
            total_credits = 0
            for code in final:
                cur.execute("SELECT CreditHours FROM Courses WHERE CourseCode = %s", (code,))
                row = cur.fetchone()
                if row:
                    total_credits += row[0]

            return {
                'retakes': retakes,
                'official': official,
                'blocked': blocked,
                'final': final,
                'total_credits': total_credits
            }