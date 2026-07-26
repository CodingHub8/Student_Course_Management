from .connection import get_connection
from .models import hash_password

def init_database():
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Users
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Users (
                    UserID SERIAL PRIMARY KEY,
                    Username TEXT UNIQUE NOT NULL,
                    Password TEXT NOT NULL,
                    Role TEXT DEFAULT 'Academic Advisor',
                    FullName TEXT,
                    Cohort TEXT,
                    Program TEXT
                );
            """)

            # Students
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Students (
                    MatricNo TEXT PRIMARY KEY,
                    Name TEXT NOT NULL,
                    CurrentCGPA REAL,
                    Class TEXT,
                    AdvisorID INTEGER REFERENCES Users(UserID) ON DELETE SET NULL,
                    TotalCreditsEarned REAL DEFAULT 0,
                    CurrentSemesterCredits REAL DEFAULT 0,
                    Program TEXT,
                    CurrentSemester INTEGER DEFAULT 1
                );
            """)

            # Courses – NO IsKokurikulum
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Courses (
                    CourseCode TEXT PRIMARY KEY,
                    CourseName TEXT NOT NULL,
                    DefaultSemester INTEGER NOT NULL,
                    CreditHours INTEGER NOT NULL,
                    Cohort TEXT,
                    Program TEXT,
                    CourseGroup TEXT
                );
            """)

            # Prerequisites
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Prerequisites (
                    ID SERIAL PRIMARY KEY,
                    CourseCode TEXT NOT NULL REFERENCES Courses(CourseCode) ON DELETE CASCADE,
                    PrereqCode TEXT NOT NULL REFERENCES Courses(CourseCode) ON DELETE CASCADE,
                    UNIQUE(CourseCode, PrereqCode)
                );
            """)

            # Enrollments
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Enrollments (
                    ID SERIAL PRIMARY KEY,
                    StudentID TEXT NOT NULL REFERENCES Students(MatricNo) ON DELETE CASCADE,
                    CourseCode TEXT NOT NULL REFERENCES Courses(CourseCode) ON DELETE CASCADE,
                    SemesterSession TEXT NOT NULL,
                    AttemptType TEXT DEFAULT 'NORMAL',
                    Grade TEXT,
                    UNIQUE(StudentID, CourseCode, SemesterSession, AttemptType)
                );
            """)

            # Safely add columns if they do not exist
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='courses';")
            course_cols = [row[0] for row in cur.fetchall()]
            if 'coursegroup' not in course_cols:
                cur.execute("ALTER TABLE Courses ADD COLUMN CourseGroup TEXT;")
            # Drop IsKokurikulum if it exists (cleanup)
            if 'iskokurikulum' in course_cols:
                cur.execute("ALTER TABLE Courses DROP COLUMN IsKokurikulum;")

            # Add CurrentSemester to Students if missing
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='students';")
            student_cols = [row[0] for row in cur.fetchall()]
            if 'currentsemester' not in student_cols:
                cur.execute("ALTER TABLE Students ADD COLUMN CurrentSemester INTEGER DEFAULT 1;")

            # Drop any old unused columns from Users
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='users';")
            user_cols = [row[0] for row in cur.fetchall()]
            if 'assignedsemester' in user_cols:
                cur.execute("ALTER TABLE Users DROP COLUMN AssignedSemester;")

            conn.commit()