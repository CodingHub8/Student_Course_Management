import pandas as pd
import pdfplumber
import re
import os
from database.models import (add_course, add_prerequisite, add_student,
                             add_enrollment, get_all_advisors)

# ---------- Excel sheet helpers ----------
def get_excel_sheet_names(file_path):
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
        text = ""
        for page in pdf.pages:
            text += page.extract_text() or ""
        pattern = r'([A-Z]{3}\d{5})\s+([A-Za-z\s]+)'
        matches = re.findall(pattern, text)
        if matches:
            df = pd.DataFrame(matches, columns=['CourseCode', 'CourseName'])
            return df
        raise ValueError("Could not parse PDF. No tables or recognizable course codes found.")

# ---------- Auto Mapping (updated with new columns) ----------
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
            elif 'prerequisite' in lc or 'prereq' in lc:
                mapping['Prerequisite'] = col
            elif 'program' in lc:
                mapping['Program'] = col
            elif 'cohort' in lc:
                mapping['Cohort'] = col
            elif 'coursegroup' in lc or 'group' in lc:
                mapping['CourseGroup'] = col
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
            elif 'advisor' in lc or 'penasihat' in lc:
                mapping['Advisor'] = col
            elif 'program' in lc:
                mapping['Program'] = col
            elif 'currentsemester' in lc or 'semester' in lc:
                mapping['CurrentSemester'] = col
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
    if code and code[-1].isdigit():
        return int(code[-1])
    return 0

def import_courses(df, required_columns):
    count = 0
    for _, row in df.iterrows():
        try:
            code = row.get('CourseCode')
            name = row.get('CourseName')
            if not code or not name:
                continue
            sem = row.get('DefaultSemester')
            if pd.isna(sem) or sem is None:
                sem = 1
            else:
                sem = int(sem)
            credits = row.get('CreditHours')
            if pd.isna(credits) or credits is None:
                credits = infer_credit_from_code(code)
            else:
                credits = int(credits)
            prereq_val = row.get('Prerequisite')
            prereq = None
            if pd.notna(prereq_val) and str(prereq_val).strip():
                prereq = str(prereq_val).strip()
            program = row.get('Program')
            if pd.isna(program) or not str(program).strip():
                program = None
            else:
                program = str(program).strip()
            cohort = row.get('Cohort')
            if pd.isna(cohort) or not str(cohort).strip():
                cohort = None
            else:
                cohort = str(cohort).strip()
            course_group = row.get('CourseGroup')
            if pd.isna(course_group) or not str(course_group).strip():
                course_group = None
            else:
                course_group = str(course_group).strip()
            # Add course
            add_course(code, name, sem, credits, cohort, program, course_group)
            if prereq:
                try:
                    add_prerequisite(code, prereq)
                except Exception as e:
                    print(f"Warning: Failed to add prerequisite {prereq} for {code}: {e}")
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
    advisors = {}
    for uid, uname, fullname, _ in get_all_advisors():
        advisors[uname] = uid
        advisors[fullname] = uid
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
            program = row.get('Program')
            if pd.isna(program) or not str(program).strip():
                program = None
            else:
                program = str(program).strip()
            current_semester = row.get('CurrentSemester')
            if pd.isna(current_semester) or current_semester is None:
                current_semester = 1
            else:
                current_semester = int(current_semester)
            add_student(matric, name, cgpa, class_name, advisor_id, program, current_semester)
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