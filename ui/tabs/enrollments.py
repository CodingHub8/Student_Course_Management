from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                               QTableWidget, QTableWidgetItem, QLabel, QHeaderView,
                               QPushButton, QMessageBox, QDialog, QFormLayout,
                               QLineEdit, QDialogButtonBox, QComboBox as QCombo,
                               QCheckBox, QGroupBox, QScrollArea)
from PySide6.QtCore import Qt, QPoint
from database.models import (get_all_students, get_students_by_advisor,
                             get_all_courses, get_student_enrollments,
                             add_enrollment, delete_enrollment, update_enrollment,
                             get_course_prerequisite, get_failed_courses,
                             get_student_cgpa, get_max_credits_by_cgpa,
                             get_student_future_courses, get_student_current_semester)
from database.connection import get_connection
from ui.dialogs.add_dialog import AddEnrollmentDialog

class EnrollmentEditDialog(QDialog):
    """Dialog to add or edit an enrollment."""
    def __init__(self, student_id, course_code, course_name, existing_enrollment=None, parent=None):
        super().__init__(parent)
        self.student_id = student_id
        self.course_code = course_code
        self.course_name = course_name
        self.existing = existing_enrollment
        self.setWindowTitle(f"Enrollment for {course_code}")
        self.setFixedSize(400, 280)
        layout = QVBoxLayout()
        form = QFormLayout()

        self.student_label = QLabel(student_id)
        form.addRow("Student:", self.student_label)

        self.course_label = QLabel(course_code + " - " + course_name)
        form.addRow("Course:", self.course_label)

        self.session_edit = QLineEdit()
        if self.existing:
            self.session_edit.setText(self.existing.get('session', ''))
        else:
            self.session_edit.setPlaceholderText("e.g., 1")
        form.addRow("Semester Diambil:", self.session_edit)

        self.attempt_combo = QCombo()
        self.attempt_combo.addItems(["NORMAL", "C1", "C2", "TANGGUH"])
        if self.existing and self.existing.get('attempt'):
            idx = self.attempt_combo.findText(self.existing['attempt'])
            if idx >= 0:
                self.attempt_combo.setCurrentIndex(idx)
        form.addRow("Attempt Type:", self.attempt_combo)

        self.grade_edit = QLineEdit()
        if self.existing:
            self.grade_edit.setText(self.existing.get('grade', ''))
        else:
            self.grade_edit.setPlaceholderText("e.g., A, B, C, D, F, TANGGUH")
        form.addRow("Grade:", self.grade_edit)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

        layout.addLayout(form)
        layout.addWidget(btn_box)
        self.setLayout(layout)

    def get_data(self):
        return {
            'session': self.session_edit.text().strip(),
            'attempt': self.attempt_combo.currentText(),
            'grade': self.grade_edit.text().strip()
        }


class EnrollmentsTab(QWidget):
    def __init__(self, advisor_id=None):
        super().__init__()
        self.advisor_id = advisor_id
        self.current_student = None
        self.current_semester = 1
        self._updating_checkbox = False

        layout = QVBoxLayout()

        # Top row: Student and Semester
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Pelajar:"))
        self.student_combo = QComboBox()
        self.student_combo.currentIndexChanged.connect(self.on_student_changed)
        top_layout.addWidget(self.student_combo)

        top_layout.addWidget(QLabel("Subjek Semester:"))
        self.semester_combo = QComboBox()
        for i in range(1, 9):
            self.semester_combo.addItem(f"{i}", i)
        self.semester_combo.currentIndexChanged.connect(self.on_semester_changed)
        top_layout.addWidget(self.semester_combo)

        top_layout.addStretch()
        layout.addLayout(top_layout)

        # Main table (checklist)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Enroll", "Code", "Course Name", "Credit", "Prerequisites", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.on_context_menu)
        layout.addWidget(self.table)

        # Recommendations group
        self.recommend_group = QGroupBox("Cadangan Subjek (Berdasarkan CGPA)")
        self.recommend_group.setVisible(False)
        rec_layout = QVBoxLayout()
        self.recommend_table = QTableWidget()
        self.recommend_table.setColumnCount(5)
        self.recommend_table.setHorizontalHeaderLabels(["Semester", "Code", "Name", "Credits", "Status"])
        self.recommend_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.recommend_table.setEditTriggers(QTableWidget.NoEditTriggers)
        rec_layout.addWidget(self.recommend_table)
        self.recommend_warning = QLabel("")
        self.recommend_warning.setStyleSheet("color: red;")
        rec_layout.addWidget(self.recommend_warning)
        self.recommend_group.setLayout(rec_layout)
        layout.addWidget(self.recommend_group)

        # Buttons
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.refresh_students()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_students()

    def refresh_students(self):
        self.student_combo.clear()
        if self.advisor_id:
            students = get_students_by_advisor(self.advisor_id)
        else:
            students = get_all_students()
        for row in students:
            if len(row) >= 2:
                matric = row[0]
                name = row[1]
                display = f"{matric} - {name}"
                self.student_combo.addItem(display, matric)
        if self.student_combo.count() > 0:
            self.on_student_changed(0)

    def on_student_changed(self, index):
        if index < 0:
            return
        self.current_student = self.student_combo.currentData()
        # Set semester to student's current semester
        sem = get_student_current_semester(self.current_student)
        idx = self.semester_combo.findData(sem)
        if idx >= 0:
            self.semester_combo.setCurrentIndex(idx)
        else:
            self.semester_combo.setCurrentIndex(0)
        self.refresh()

    def on_semester_changed(self, index):
        if index >= 0:
            self.current_semester = self.semester_combo.currentData()
            self.refresh()

    def refresh(self):
        if not self.current_student:
            return

        # Fetch courses for selected semester
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT CourseCode, CourseName, DefaultSemester, CreditHours, CourseGroup
                    FROM Courses
                    WHERE DefaultSemester = %s
                    ORDER BY CourseCode
                """, (self.current_semester,))
                current_courses = cur.fetchall()

        # Get failed courses from previous semesters
        failed = get_failed_courses(self.current_student)
        failed_codes = [f[0] for f in failed]

        # Combine: current courses + failed (if not already present)
        all_courses = list(current_courses)
        for fc in failed:
            if not any(c[0] == fc[0] for c in all_courses):
                with get_connection() as conn2:
                    with conn2.cursor() as cur2:
                        cur2.execute("SELECT CourseName, DefaultSemester, CreditHours, CourseGroup FROM Courses WHERE CourseCode = %s", (fc[0],))
                        row = cur2.fetchone()
                        if row:
                            all_courses.append((fc[0], row[0], row[1], row[2], row[3], True))  # carry-over flag

        # Get enrollments
        enrollments = get_student_enrollments(self.current_student)
        enrollment_map = {}
        passed_courses = set()
        for e in enrollments:
            course = e[2]
            grade = e[5] if e[5] else ''
            enrollment_map[course] = {
                'id': e[0],
                'session': e[3],
                'attempt': e[4],
                'grade': grade
            }
            if grade in ('A', 'B', 'C'):
                passed_courses.add(course)

        # Build rows
        rows = []
        for course in all_courses:
            if len(course) == 5:
                code, name, sem, cred, is_koku = course
                is_carry = False
            else:
                code, name, sem, cred, is_koku, is_carry = course
            if code in passed_courses:
                continue
            info = enrollment_map.get(code)
            status = "Not Enrolled"
            if info:
                grade = info['grade'] if info['grade'] else "No Grade"
                attempt = info['attempt'] if info['attempt'] else "NORMAL"
                status = f"{grade} ({attempt})"
            disabled = info is not None and info['grade'] != ''
            rows.append({
                'code': code,
                'name': name,
                'credits': cred,
                'enrolled': info is not None,
                'status': status,
                'enrollment_id': info['id'] if info else None,
                'disabled': disabled,
                'is_carry': is_carry
            })

        rows.sort(key=lambda x: (not x['is_carry'], x['code']))

        self.table.setRowCount(len(rows))
        self._updating_checkbox = True
        for i, row in enumerate(rows):
            cb = QCheckBox()
            cb.setChecked(row['enrolled'])
            cb.setEnabled(not row['disabled'])
            # Connect the clicked signal to open the dialog
            cb.clicked.connect(lambda checked, row_idx=i: self.on_checkbox_clicked(row_idx))
            self.table.setCellWidget(i, 0, cb)
            self.table.setItem(i, 1, QTableWidgetItem(row['code']))
            self.table.setItem(i, 2, QTableWidgetItem(row['name']))
            self.table.setItem(i, 3, QTableWidgetItem(str(row['credits'])))
            prereqs = get_course_prerequisite(row['code'])
            prereq_str = ", ".join(prereqs)
            self.table.setItem(i, 4, QTableWidgetItem(prereq_str))
            self.table.setItem(i, 5, QTableWidgetItem(row['status']))
        self._updating_checkbox = False
        self.table.resizeColumnsToContents()

        # Recommendations
        rec_data = get_student_future_courses(self.current_student, self.current_semester)
        if rec_data['recommended']:
            self.recommend_group.setVisible(True)
            rec_table = self.recommend_table
            rec_table.setRowCount(len(rec_data['recommended']))
            for i, rec in enumerate(rec_data['recommended']):
                rec_table.setItem(i, 0, QTableWidgetItem(str(rec['semester'])))
                rec_table.setItem(i, 1, QTableWidgetItem(rec['code']))
                rec_table.setItem(i, 2, QTableWidgetItem(rec['name']))
                rec_table.setItem(i, 3, QTableWidgetItem(str(rec['credits'])))
                status = "Dropped Prerequisite" if rec['is_dropped'] else "Prerequisite OK"
                rec_table.setItem(i, 4, QTableWidgetItem(status))
            rec_table.resizeColumnsToContents()
            total_cred = rec_data['total_credits']
            max_cred = rec_data['max_credits']
            if total_cred > max_cred:
                self.recommend_warning.setText(f"Kredit melebihi jumlah yang dicadangkan ({total_cred} > {max_cred}). Pastikan pelajar mampu mengikuti subjek yang diberikan.")
                self.recommend_warning.setStyleSheet("color: red; font-weight: bold;")
            else:
                self.recommend_warning.setText(f"Jumlah kredit yang dicadangkan: {total_cred} (maksimum dicadangkan: {max_cred})")
                self.recommend_warning.setStyleSheet("color: green;")
        else:
            self.recommend_group.setVisible(False)

    def on_checkbox_clicked(self, row):
        """Open the enrollment dialog when the checkbox is clicked."""
        cb = self.table.cellWidget(row, 0)
        if not isinstance(cb, QCheckBox):
            return

        course_code = self.table.item(row, 1).text()
        course_name = self.table.item(row, 2).text()
        status_item = self.table.item(row, 5)
        status_text = status_item.text() if status_item else "Not Enrolled"

        existing = None
        if status_text != "Not Enrolled":
            enrollments = get_student_enrollments(self.current_student)
            for e in enrollments:
                if e[2] == course_code:
                    existing = {
                        'id': e[0],
                        'session': e[3],
                        'attempt': e[4],
                        'grade': e[5]
                    }
                    break

        dialog = EnrollmentEditDialog(self.current_student, course_code, course_name, existing, self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                if existing:
                    update_enrollment(existing['id'], data['grade'], data['attempt'], data['session'])
                else:
                    # Determine attempt type based on fail count
                    with get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                SELECT COUNT(*) FROM Enrollments
                                WHERE StudentID = %s AND CourseCode = %s AND Grade IN ('D', 'F', 'TANGGUH')
                            """, (self.current_student, course_code))
                            fail_count = cur.fetchone()[0]
                    attempt_type = data['attempt'] if data['attempt'] != "NORMAL" else ("C1" if fail_count == 1 else ("C2" if fail_count >= 2 else "NORMAL"))
                    add_enrollment(self.current_student, course_code, data['session'], attempt_type, data['grade'])
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save enrollment: {str(e)}")
                self.refresh()  # revert
        else:
            # Dialog canceled – revert checkbox state by refreshing
            self.refresh()

    # ---------- Right‑click context menu ----------
    def on_context_menu(self, pos: QPoint):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        course_code = self.table.item(row, 1).text()
        status_item = self.table.item(row, 5)
        status_text = status_item.text() if status_item else ""
        if status_text == "Not Enrolled":
            QMessageBox.information(self, "Info", "Student is not enrolled in this course.")
            return
        reply = QMessageBox.question(self, "Remove Enrollment",
                                     f"Remove enrollment for {course_code}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            enrollments = get_student_enrollments(self.current_student)
            for e in enrollments:
                if e[2] == course_code:
                    try:
                        delete_enrollment(e[0])
                        self.refresh()
                    except Exception as ex:
                        QMessageBox.critical(self, "Error", f"Failed to remove: {str(ex)}")
                    break