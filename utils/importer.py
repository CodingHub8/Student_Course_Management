import pandas as pd
import pdfplumber
import re
import os
from database.models import (add_course, add_prerequisite, add_student,
                             add_enrollment, get_all_advisors)
from database.connection import get_connection

# ---------- Excel sheet helpers ----------
def get_excel_sheet_names(file_path):
    """Return list of sheet names in an Excel file."""
    xl = pd.ExcelFile(file_path)
    return xl.sheet_names

# ---------- Parsing with sheet selection ----------
def parse_file(file_path, sheet_name=None):
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ['.csv', '.txt']:
        for delim in [',', ';', '\t', '|']:
            try:
                df = pd.read_csv(file_path, sep=delim, encoding='utf-8', nrows=10)
                if df.shape[1] > 1:
                    return pd.read_csv(file_path, sep=delim, encoding='utf-8')
            except:
                continue
        return pd.read_csv(file_path, encoding='utf-8')
    elif ext in ['.xlsx', '.xls']:
        if sheet_name:
            return pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            return pd.read_excel(file_path)
    elif ext == '.pdf':
        return parse_pdf(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

def parse_pdf(file_path):
    with pdfplumber.open(file_path) as pdf:
        all_tables = []
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if table and len(table) > 1:
                    all_tables.extend(table)
        if all_tables:
            header = None
            data_rows = []
            for row in all_tables:
                if not any(cell for cell in row):
                    continue
                if header is None:
                    header = [str(cell).strip() if cell else '' for cell in row]
                else:
                    data_rows.append(row)
            if header and data_rows:
                df = pd.DataFrame(data_rows, columns=header)
                df.columns = [re.sub(r'\s+', ' ', col).strip() for col in df.columns]
                df = df.loc[:, df.columns.str.len() > 0]
                return df
        # Fallback to regex – only captures Code and Name, no credits
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
        pattern = r'([A-Z]{3}\d{5})\s+([A-Za-z\s]+)'
        matches = re.findall(pattern, text)
        if matches:
            df = pd.DataFrame(matches, columns=['CourseCode', 'CourseName'])
            return df
        raise ValueError("Could not parse PDF. No tables or recognizable course codes found.")

# ---------- Auto Mapping ----------
def auto_map_columns(columns, import_type):
    mapping = {}
    if import_type in ['All', 'Courses']:
        for col in columns:
            lc = col.lower().strip()
            if 'coursecode' in lc or 'code' in lc or 'course code' in lc:
                mapping['CourseCode'] = col
            elif 'coursename' in lc or 'course' in lc or 'course name' in lc:
                mapping['CourseName'] = col
            elif 'defaultsemester' in lc or 'semester' in lc:
                mapping['DefaultSemester'] = col
            elif 'credithours' in lc or 'credits' in lc or 'credit' in lc:
                mapping['CreditHours'] = col
    if import_type in ['All', 'Prerequisites']:
        for col in columns:
            lc = col.lower().strip()
            if 'course' in lc and 'prereq' not in lc:
                mapping['CourseCode'] = col
            elif 'prereq' in lc:
                mapping['PrereqCode'] = col
    if import_type in ['All', 'Students']:
        for col in columns:
            lc = col.lower().strip()
            if 'matric' in lc or 'studentid' in lc or 'id' in lc:
                mapping['MatricNo'] = col
            elif 'name' in lc or 'nama' in lc:
                mapping['Name'] = col
            elif 'cgpa' in lc or 'gpa' in lc or 'pnm' in lc or 'hpnm' in lc:
                mapping['CurrentCGPA'] = col
            elif 'kelas' in lc or 'class' in lc:
                mapping['Class'] = col
            elif 'Academic Advisor' in lc or 'penasihat' in lc:
                mapping['Advisor'] = col
    if import_type in ['All', 'Enrollments']:
        for col in columns:
            lc = col.lower().strip()
            if 'student' in lc and ('id' in lc or 'matric' in lc):
                mapping['StudentID'] = col
            elif 'course' in lc and 'code' in lc:
                mapping['CourseCode'] = col
            elif 'semester' in lc and 'session' in lc:
                mapping['SemesterSession'] = col
            elif 'attempt' in lc or 'type' in lc:
                mapping['AttemptType'] = col
            elif 'grade' in lc:
                mapping['Grade'] = col
    return mapping

# ---------- Import Functions ----------
def infer_credit_from_code(code):
    """Get credit from last digit of course code (common convention)."""
    if code and code[-1].isdigit():
        return int(code[-1])
    return 0

def import_courses(df, required_columns):
    """
    Import courses from a DataFrame.
    Expected columns: CourseCode, CourseName, DefaultSemester, CreditHours.
    If CreditHours is missing or 0, infer from last digit of CourseCode.
    """
    count = 0
    for _, row in df.iterrows():
        try:
            code = row.get('CourseCode')
            name = row.get('CourseName')
            if not code or not name:
                continue
            sem = int(row.get('DefaultSemester', 1))
            credits = int(row.get('CreditHours', 0))
            # If credits is 0, try to infer from last digit
            if credits == 0:
                credits = infer_credit_from_code(code)
            add_course(code, name, sem, credits)
            count += 1
        except Exception as e:
            print(f"Error importing course {row}: {e}")
            continue
    return count

def import_prerequisites(df, required_columns):
    count = 0
    for _, row in df.iterrows():
        try:
            course = row.get('CourseCode')
            prereq = row.get('PrereqCode')
            if not course or not prereq:
                continue
            add_prerequisite(course, prereq)
            count += 1
        except:
            continue
    return count

def import_students(df, required_columns):
    count = 0
    advisors = {uname: uid for uid, uname, _ in get_all_advisors()}
    for _, row in df.iterrows():
        try:
            matric = row.get('MatricNo')
            name = row.get('Name')
            if not matric or not name:
                continue
            cgpa = float(row.get('CurrentCGPA', 0.0)) if row.get('CurrentCGPA') else 0.0
            class_name = row.get('Class', '')
            advisor_name = row.get('Advisor', '').strip()
            advisor_id = None
            if advisor_name:
                advisor_id = advisors.get(advisor_name)
                if advisor_id is None:
                    print(f"Warning: Advisor '{advisor_name}' not found. Student will be unassigned.")
            add_student(matric, name, cgpa, class_name, advisor_id)
            count += 1
        except Exception as e:
            print(f"Error importing student {row}: {e}")
            continue
    return count

def import_enrollments(df, required_columns):
    count = 0
    for _, row in df.iterrows():
        try:
            student = row.get('StudentID')
            course = row.get('CourseCode')
            session = row.get('SemesterSession')
            if not student or not course or not session:
                continue
            attempt = row.get('AttemptType', 'NORMAL')
            grade = row.get('Grade', '')
            add_enrollment(student, course, session, attempt, grade)
            count += 1
        except:
            continue
    return count