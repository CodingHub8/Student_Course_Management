from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QComboBox, QLineEdit, QPushButton, QMessageBox, QLabel, \
    QCheckBox, QSpinBox, QRadioButton, QHBoxLayout
from database.models import (get_all_students, get_all_courses, get_all_advisors,
                             get_students_by_advisor_for_dropdown, GRADE_POINTS, clean_course_code)

class AddEnrollmentDialog(QDialog):
    def __init__(self, semester, advisor_id=None):
        super().__init__()
        self.advisor_id = advisor_id
        self.semester = semester
        self.setWindowTitle("Add Enrollment")
        self.setFixedSize(400, 350)
        layout = QVBoxLayout()
        form = QFormLayout()

        self.student_combo = QComboBox()
        if advisor_id:
            students = get_students_by_advisor_for_dropdown(advisor_id)
        else:
            students = get_all_students()
        for matric, name in students:
            self.student_combo.addItem(f"{matric} - {name}", matric)

        self.course_combo = QComboBox()
        courses = get_all_courses()
        for course in courses:
            code, name, sem, cred, cohort = course[:5]
            if sem == semester:
                self.course_combo.addItem(f"{clean_course_code(code)} - {name}", code)

        self.session_edit = QLineEdit()
        self.session_edit.setPlaceholderText("e.g., 2025/2026-SEM2")

        self.attempt_combo = QComboBox()
        self.attempt_combo.addItems(["NORMAL", "C1", "C2", "C3", "TANGGUH"])

        self.grade_combo = QComboBox()
        self.grade_combo.addItem("In Progress", None)
        for grade in sorted(GRADE_POINTS.keys(), key=lambda x: GRADE_POINTS[x] if GRADE_POINTS[x] is not None else -1, reverse=True):
            self.grade_combo.addItem(grade, grade)

        self.pass_label = QLabel("Pass Status:")
        self.pass_combo = QComboBox()
        self.pass_combo.addItems(["LULUS", "GAGAL", "TANGGUH"])

        # Connect grade change to update pass status
        self.grade_combo.currentIndexChanged.connect(self.on_grade_changed)

        form.addRow("Student:", self.student_combo)
        form.addRow("Course:", self.course_combo)
        form.addRow("Semester Session:", self.session_edit)
        form.addRow("Attempt Type:", self.attempt_combo)
        form.addRow("Grade:", self.grade_combo)
        form.addRow(self.pass_label, self.pass_combo)

        # Initial state
        self.update_pass_status(self.grade_combo.currentData())

        btn_ok = QPushButton("Add")
        btn_ok.clicked.connect(self.accept)

        layout.addLayout(form)
        layout.addWidget(btn_ok)
        self.setLayout(layout)

    def on_grade_changed(self, index):
        grade = self.grade_combo.currentData()
        self.update_pass_status(grade)

    def update_pass_status(self, grade):
        self.pass_combo.blockSignals(True)
        model = self.pass_combo.model()

        def set_item_enabled(text, enabled):
            for i in range(self.pass_combo.count()):
                if self.pass_combo.itemText(i) == text:
                    item = model.item(i) if model else None
                    if item:
                        item.setEnabled(enabled)

        if grade is None or grade == 'In Progress':
            self.pass_label.setVisible(False)
            self.pass_combo.setVisible(False)
            self.pass_combo.setCurrentIndex(0)
        else:
            self.pass_label.setVisible(True)
            self.pass_combo.setVisible(True)
            if model:
                for i in range(self.pass_combo.count()):
                    item = model.item(i)
                    if item:
                        item.setEnabled(True)

            if grade in ('E', 'E-', 'F'):
                self.pass_combo.setCurrentText("GAGAL")
                set_item_enabled("LULUS", False)
                set_item_enabled("TANGGUH", False)
            elif grade == 'TANGGUH':
                self.pass_combo.setCurrentText("TANGGUH")
                set_item_enabled("LULUS", False)
                set_item_enabled("GAGAL", False)
            elif GRADE_POINTS.get(grade, -1) >= 1.00:
                if not self.pass_combo.currentText() or self.pass_combo.currentText() == "TANGGUH":
                    self.pass_combo.setCurrentText("LULUS")
                set_item_enabled("TANGGUH", False)
        self.pass_combo.blockSignals(False)

    def get_data(self):
        grade = self.grade_combo.currentData()
        pass_status = self.pass_combo.currentText().strip() if self.pass_combo.isVisible() and grade is not None else None
        return {
            'student_id': self.student_combo.currentData(),
            'course_code': self.course_combo.currentData(),
            'semester_session': self.session_edit.text().strip(),
            'attempt_type': self.attempt_combo.currentText(),
            'grade': grade,
            'pass_status': pass_status
        }

class AddCourseDialog(QDialog):
    def __init__(self, current_user_id=None, current_role=None, user_cohort=None, user_program=None):
        super().__init__()
        self.current_role = current_role
        self.user_cohort = user_cohort
        self.user_program = user_program
        self.setWindowTitle("Add Course")
        self.setFixedSize(450, 480 if current_role in ('admin', 'System Administrator') else 400)
        layout = QVBoxLayout()
        form = QFormLayout()

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("e.g., DEC30182")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Course Name")
        self.sem_edit = QLineEdit()
        self.sem_edit.setPlaceholderText("Semester (1-6)")
        self.cred_edit = QLineEdit()
        self.cred_edit.setPlaceholderText("Credit Hours")

        self.prereq_edit = QLineEdit()
        self.prereq_edit.setPlaceholderText("Leave empty if none (comma-separated codes)")

        self.koku_check = QRadioButton("Kokurikulum (contoh, Sukan, Kelab/Persatuan, Unit Beruniform)")
        self.mpu_check = QRadioButton("Subjek Khas (contoh, Sains Islam, Nilai Masyarakat Malaysia)")
        self.elective_check = QRadioButton("Subjek Elektif")

        self.cohort_edit = QLineEdit()
        self.cohort_edit.setPlaceholderText("e.g., SESI 1 2025/2026")
        if current_role in ('admin', 'System Administrator'):
            self.cohort_edit.setVisible(True)
        else:
            self.cohort_edit.setVisible(False)
            self.cohort_edit.setText(user_cohort if user_cohort else "")

        self.program_combo = QComboBox()
        self.program_combo.addItems(["DEE", "DDT", "DET", "Other"])
        self.program_combo.currentIndexChanged.connect(self.on_program_changed)
        self.program_other_edit = QLineEdit()
        self.program_other_edit.setPlaceholderText("Enter other program name")
        self.program_other_edit.setVisible(False)

        if current_role in ('admin', 'System Administrator'):
            self.program_combo.setVisible(True)
            self.program_other_edit.setVisible(False)
        else:
            self.program_combo.setVisible(False)
            self.program_other_edit.setVisible(False)
            if user_program:
                idx = self.program_combo.findText(user_program)
                if idx >= 0:
                    self.program_combo.setCurrentIndex(idx)
                else:
                    self.program_combo.setCurrentText("Other")
                    self.program_other_edit.setText(user_program)
                    self.program_other_edit.setVisible(True)

        form.addRow("Course Code:", self.code_edit)
        form.addRow("Name:", self.name_edit)
        form.addRow("Default Semester:", self.sem_edit)
        form.addRow("Credits:", self.cred_edit)

        if current_role in ('admin', 'System Administrator'):
            form.addRow("Cohort:", self.cohort_edit)
            prog_layout = QHBoxLayout()
            prog_layout.addWidget(self.program_combo)
            prog_layout.addWidget(self.program_other_edit)
            form.addRow("Program:", prog_layout)
            form.addRow("Course Group:", self.koku_check)
            form.addRow("", self.mpu_check)
            form.addRow("", self.elective_check)

        form.addRow("Prerequisites:", self.prereq_edit)

        btn_ok = QPushButton("Add")
        btn_ok.clicked.connect(self.accept)

        layout.addLayout(form)
        layout.addWidget(btn_ok)
        self.setLayout(layout)

    def on_program_changed(self, index):
        if self.program_combo.currentText() == "Other":
            self.program_other_edit.setVisible(True)
        else:
            self.program_other_edit.setVisible(False)
            self.program_other_edit.clear()

    def get_data(self):
        prereq_str = self.prereq_edit.text().strip()
        prereq_list = [p.strip() for p in prereq_str.split(',') if p.strip()] if prereq_str else []
        cohort_val = self.cohort_edit.text().strip().upper() if self.cohort_edit.text().strip() else None

        if self.program_combo.isVisible():
            if self.program_combo.currentText() == "Other":
                program_val = self.program_other_edit.text().strip().upper()
                if not program_val:
                    program_val = "OTHER"
            else:
                program_val = self.program_combo.currentText().strip().upper()
        else:
            program_val = None

        if self.koku_check.isChecked():
            group_val = "KOKURIKULUM"
        elif self.mpu_check.isChecked():
            group_val = "SUBJEK KHAS"
        elif self.elective_check.isChecked():
            group_val = "ELEKTIF"
        else:
            group_val = None

        return {
            'code': self.code_edit.text().strip(),
            'name': self.name_edit.text().strip(),
            'semester': int(self.sem_edit.text()) if self.sem_edit.text().isdigit() else 1,
            'credits': int(self.cred_edit.text()) if self.cred_edit.text().isdigit() else 0,
            'prerequisites': prereq_list,
            'cohort': cohort_val,
            'program': program_val,
            'course_group': group_val
        }


class AddPrereqDialog(QDialog):
    def __init__(self, preselected_course=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Prerequisite")
        self.setFixedSize(400, 150)
        layout = QVBoxLayout()
        form = QFormLayout()

        self.course_combo = QComboBox()
        self.prereq_combo = QComboBox()
        self.koku_check = QCheckBox("Kokurikulum")
        courses = get_all_courses()
        for course in courses:
            code, name = course[0], course[1]
            display = f"{clean_course_code(code)} - {name}"
            self.course_combo.addItem(display, code)
            self.prereq_combo.addItem(display, code)

        if preselected_course:
            index = self.course_combo.findData(preselected_course)
            if index >= 0:
                self.course_combo.setCurrentIndex(index)
                self.course_combo.setEnabled(False)

        form.addRow("Course:", self.course_combo)
        form.addRow("Prerequisite:", self.prereq_combo)

        btn_ok = QPushButton("Add")
        btn_ok.clicked.connect(self.accept)

        layout.addLayout(form)
        layout.addWidget(btn_ok)
        self.setLayout(layout)

    def get_data(self):
        return {
            'course': self.course_combo.currentData(),
            'prereq': self.prereq_combo.currentData(),
            'is_kokurikulum': self.koku_check.isChecked()
        }


class AddStudentDialog(QDialog):
    def __init__(self, current_user_id=None, current_role=None, user_program=None):
        super().__init__()
        self.current_user_id = current_user_id
        self.current_role = current_role
        self.user_program = user_program
        self.setWindowTitle("Add Student")
        self.setFixedSize(450, 300)
        layout = QVBoxLayout()
        form = QFormLayout()

        self.matric_edit = QLineEdit()
        self.matric_edit.setPlaceholderText("e.g., 25DEE25F0000")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Full Name")
        self.cgpa_edit = QLineEdit()
        self.cgpa_edit.setPlaceholderText("e.g., 4.00")
        self.class_edit = QLineEdit()
        self.class_edit.setPlaceholderText("e.g., DEE1A")
        self.semester_spin = QSpinBox()
        self.semester_spin.setRange(1, 8)
        self.semester_spin.setValue(1)

        self.program_combo = QComboBox()
        self.program_combo.addItems(["DEE", "DDT", "DET", "Other"])
        self.program_other_edit = QLineEdit()
        self.program_other_edit.setPlaceholderText("Enter other program name")
        self.program_other_edit.setVisible(False)
        self.program_combo.currentIndexChanged.connect(self.on_program_changed)

        if current_role in ('admin', 'System Administrator'):
            self.program_combo.setVisible(True)
            self.program_other_edit.setVisible(False)
        else:
            self.program_combo.setVisible(False)
            self.program_other_edit.setVisible(False)
            if user_program:
                idx = self.program_combo.findText(user_program)
                if idx >= 0:
                    self.program_combo.setCurrentIndex(idx)
                else:
                    self.program_combo.setCurrentText("Other")
                    self.program_other_edit.setText(user_program)
                    self.program_other_edit.setVisible(True)

        self.advisor_combo = QComboBox()
        advisors = get_all_advisors()
        if advisors:
            for uid, uname, fullname, prog in advisors:
                display = f"{fullname} ({uname})"
                self.advisor_combo.addItem(display, uid)
        else:
            self.advisor_combo.addItem("No advisors available", None)

        if current_role == 'Academic Advisor' and current_user_id:
            self.advisor_combo.setVisible(False)
            self._fixed_advisor_id = current_user_id
        else:
            self.advisor_combo.setVisible(True)
            self._fixed_advisor_id = None

        form.addRow("Nombor Matrik:", self.matric_edit)
        form.addRow("Nama:", self.name_edit)
        form.addRow("HPNM:", self.cgpa_edit)
        form.addRow("Kelas:", self.class_edit)
        form.addRow("Semester Terkini:", self.semester_spin)

        if current_role in ('admin', 'System Administrator'):
            prog_layout = QHBoxLayout()
            prog_layout.addWidget(self.program_combo)
            prog_layout.addWidget(self.program_other_edit)
            form.addRow("Program:", prog_layout)
            form.addRow("Penasihat Akademik:", self.advisor_combo)

        btn_ok = QPushButton("Add")
        btn_ok.clicked.connect(self.accept)

        layout.addLayout(form)
        layout.addWidget(btn_ok)
        self.setLayout(layout)

    def on_program_changed(self, index):
        if self.program_combo.currentText() == "Other":
            self.program_other_edit.setVisible(True)
        else:
            self.program_other_edit.setVisible(False)
            self.program_other_edit.clear()

    def get_data(self):
        cgpa = 0.0
        try:
            cgpa = float(self.cgpa_edit.text().strip()) if self.cgpa_edit.text().strip() else 0.0
        except ValueError:
            pass

        if self.program_combo.isVisible():
            if self.program_combo.currentText() == "Other":
                program_val = self.program_other_edit.text().strip().upper()
                if not program_val:
                    program_val = "OTHER"
            else:
                program_val = self.program_combo.currentText().strip().upper()
        else:
            program_val = self.user_program

        if self.current_role == 'Academic Advisor':
            advisor_id = self._fixed_advisor_id
        else:
            advisor_id = self.advisor_combo.currentData()

        return {
            'matric': self.matric_edit.text().strip(),
            'name': self.name_edit.text().strip(),
            'cgpa': cgpa,
            'class': self.class_edit.text().strip(),
            'advisor_id': advisor_id,
            'program': program_val,
            'current_semester': self.semester_spin.value()
        }