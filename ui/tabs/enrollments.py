from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                               QTableWidget, QTableWidgetItem, QLabel, QHeaderView,
                               QPushButton, QMessageBox, QDialog, QFormLayout,
                               QLineEdit, QDialogButtonBox, QComboBox as QCombo,
                               QCheckBox, QGroupBox, QScrollArea, QApplication, QTabWidget)
from PySide6.QtCore import Qt, QPoint
from database.models import (get_all_students, get_students_by_advisor,
                             get_all_courses, get_student_enrollments,
                             add_enrollment, delete_enrollment, update_enrollment,
                             get_course_prerequisite, get_failed_courses,
                             get_student_cgpa, get_max_credits_by_cgpa,
                             get_student_future_courses, get_student_current_semester,
                             GRADE_POINTS, clean_course_code, get_default_session,
                             get_semester_number_from_session, get_cached_courses)
from database.connection import get_connection
from ui.dialogs.add_dialog import AddEnrollmentDialog


def format_enrollment_status(pass_status, grade, attempt):
    if pass_status == 'LULUS' and grade and GRADE_POINTS.get(grade, -1) >= 1.00:
        base = f"LULUS ({grade})"
    elif pass_status == 'GAGAL' or (grade in ('E', 'E-', 'F')):
        base = f"GAGAL ({grade})" if grade else "GAGAL"
    elif pass_status == 'TANGGUH' or grade == 'TANGGUH':
        base = "TANGGUH"
    else:
        base = "Dalam Progres"

    if attempt and attempt != 'NORMAL':
        return f"{attempt} - {base}"
    return base


class EnrollmentEditDialog(QDialog):
    def __init__(self, student_id, course_code, course_name, current_semester=1, advisor_id=None, existing_enrollment=None, parent=None):
        super().__init__(parent)
        self.student_id = student_id
        self.course_code = course_code
        self.course_name = course_name
        self.current_semester = current_semester
        self.advisor_id = advisor_id
        self.existing = existing_enrollment
        self.setWindowTitle(f"Enrollment for {clean_course_code(course_code)}")
        self.setFixedSize(420, 380)
        layout = QVBoxLayout()
        form = QFormLayout()

        self.student_label = QLabel(student_id)
        form.addRow("Student:", self.student_label)

        self.course_label = QLabel(clean_course_code(course_code) + " - " + course_name)
        form.addRow("Course:", self.course_label)

        self.session_edit = QLineEdit()
        if self.existing and self.existing.get('session'):
            self.session_edit.setText(self.existing.get('session'))
        else:
            default_sess = get_default_session(self.advisor_id, self.current_semester)
            self.session_edit.setText(default_sess)
        form.addRow("Sesi / Semester Session:", self.session_edit)

        self.attempt_combo = QCombo()
        self.attempt_combo.addItems(["NORMAL", "C1", "C2", "TANGGUH"])

        fail_count = 0
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT COUNT(*) FROM Enrollments
                        WHERE StudentID = %s AND CourseCode = %s AND PassStatus = 'GAGAL'
                    """, (self.student_id, self.course_code))
                    fail_count = cur.fetchone()[0]
        except Exception:
            pass

        if self.existing and self.existing.get('attempt'):
            idx = self.attempt_combo.findText(self.existing['attempt'])
            if idx >= 0:
                self.attempt_combo.setCurrentIndex(idx)
        else:
            if fail_count == 1:
                idx = self.attempt_combo.findText("C1")
                if idx >= 0:
                    self.attempt_combo.setCurrentIndex(idx)
            elif fail_count >= 2:
                idx = self.attempt_combo.findText("C2")
                if idx >= 0:
                    self.attempt_combo.setCurrentIndex(idx)

        # Disable selection for NORMAL if fail_count >= 1 (attempt_count > 1)
        if fail_count >= 1:
            normal_idx = self.attempt_combo.findText("NORMAL")
            if normal_idx >= 0:
                item = self.attempt_combo.model().item(normal_idx)
                if item:
                    item.setEnabled(False)

        form.addRow("Attempt Type:", self.attempt_combo)

        # Grade dropdown with dynamic Pass Status behavior
        self.grade_combo = QCombo()
        self.grade_combo.addItem("In Progress", None)
        for grade in sorted(GRADE_POINTS.keys(), key=lambda x: GRADE_POINTS[x] if GRADE_POINTS[x] is not None else -1, reverse=True):
            self.grade_combo.addItem(grade, grade)
        if self.existing and self.existing.get('grade'):
            idx = self.grade_combo.findData(self.existing['grade'])
            if idx >= 0:
                self.grade_combo.setCurrentIndex(idx)
        self.grade_combo.currentIndexChanged.connect(self.on_grade_changed)
        form.addRow("Grade:", self.grade_combo)

        # Pass Status dropdown – dynamically updated based on grade
        self.pass_label = QLabel("Pass Status:")
        self.pass_combo = QCombo()
        self.pass_combo.addItems(["LULUS", "GAGAL", "TANGGUH"])
        if self.existing and self.existing.get('pass_status'):
            idx = self.pass_combo.findText(self.existing['pass_status'])
            if idx >= 0:
                self.pass_combo.setCurrentIndex(idx)
        else:
            self.pass_combo.setCurrentIndex(0)

        form.addRow(self.pass_label, self.pass_combo)

        # Initial state
        self.update_pass_status_options()

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

        layout.addLayout(form)
        layout.addWidget(btn_box)
        self.setLayout(layout)

    def on_grade_changed(self, index):
        self.update_pass_status_options()

    def update_pass_status_options(self):
        grade = self.grade_combo.currentData()
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

    def get_data(self):
        grade_val = self.grade_combo.currentData()
        pass_val = self.pass_combo.currentText().strip() if self.pass_combo.isVisible() and grade_val is not None else None
        return {
            'session': self.session_edit.text().strip(),
            'attempt': self.attempt_combo.currentText(),
            'grade': grade_val,
            'pass_status': pass_val
        }


class EnrollmentsTab(QWidget):
    def __init__(self, advisor_id=None):
        super().__init__()
        self.advisor_id = advisor_id
        self.current_student = None
        self.current_semester = 1
        self._updating_checkbox = False

        layout = QVBoxLayout()

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

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Enroll", "Code", "Course Name", "Credit", "Prerequisites", "Status"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Interactive)
        header.setSectionResizeMode(5, QHeaderView.Interactive)
        self.table.setColumnWidth(0, 55)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(3, 60)
        self.table.setColumnWidth(4, 130)
        self.table.setColumnWidth(5, 170)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.on_context_menu)
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        layout.addWidget(self.table)

        # Upgraded Study Plan & Summarization Group
        self.summary_group = QGroupBox("Rumusan Pengajian & Cadangan Unjuran (Study Plan Summary)")
        self.summary_group.setVisible(False)
        sum_layout = QVBoxLayout()

        self.summary_tabs = QTabWidget()

        # Tab 1: Current Semester Recommended Plan
        plan_tab_widget = QWidget()
        plan_tab_layout = QVBoxLayout(plan_tab_widget)
        self.plan_table = QTableWidget()
        self.plan_table.setColumnCount(6)
        self.plan_table.setHorizontalHeaderLabels(["Semester Default", "Code", "Course Name", "Credits", "Jenis / Status", "Penawaran Sesi Ini"])
        self.plan_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.plan_table.setEditTriggers(QTableWidget.NoEditTriggers)
        plan_tab_layout.addWidget(self.plan_table)
        self.summary_tabs.addTab(plan_tab_widget, "Cadangan Unjuran Sesi Ini")

        # Tab 2: Semester History Overview (Sem 1 to Sem 8)
        history_tab_widget = QWidget()
        history_tab_layout = QVBoxLayout(history_tab_widget)
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["Semester", "Jumlah Kredit Enrol", "Bilangan Subjek", "Status Rekod"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        history_tab_layout.addWidget(self.history_table)
        self.summary_tabs.addTab(history_tab_widget, "Ringkasan Kredit Mengikut Semester")

        sum_layout.addWidget(self.summary_tabs)

        self.summary_warning = QLabel("")
        sum_layout.addWidget(self.summary_warning)

        self.summary_group.setLayout(sum_layout)
        layout.addWidget(self.summary_group)

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

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            QApplication.processEvents()

            # Get all courses for the selected semester
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT CourseCode, CourseName, DefaultSemester, CreditHours, CourseGroup
                        FROM Courses
                        WHERE DefaultSemester = %s
                        ORDER BY CourseCode
                    """, (self.current_semester,))
                    current_courses = cur.fetchall()

            # Get all enrollments for this student
            enrollments = get_student_enrollments(self.current_student)

            # Build map by (clean_course_code, sem_num) -> enrollment info
            enrollment_map = {}
            for e in enrollments:
                clean_code = clean_course_code(e[2])
                sem_num = get_semester_number_from_session(e[3])
                key = (clean_code, sem_num)
                enrollment_map[key] = {
                    'id': e[0],
                    'course_code': e[2],
                    'session': e[3],
                    'attempt': e[4],
                    'grade': e[5],
                    'pass_status': e[6]
                }

            # Identify passed courses
            all_passed_codes = set()
            prior_passed_codes = set()
            for e in enrollments:
                if e[6] == 'LULUS' and e[5] and GRADE_POINTS.get(e[5], -1) >= 1.00:
                    clean_c = clean_course_code(e[2])
                    all_passed_codes.add(clean_c)
                    s_num = get_semester_number_from_session(e[3])
                    if s_num and s_num < self.current_semester:
                        prior_passed_codes.add(clean_c)

            # Get failed courses from any semester
            failed = get_failed_courses(self.current_student)
            failed_codes = {clean_course_code(f[0]) for f in failed if clean_course_code(f[0]) not in all_passed_codes}

            # Un-passed / un-enrolled courses from previous semesters (sem < current_semester)
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT CourseCode, DefaultSemester, CourseGroup FROM Courses WHERE DefaultSemester < %s
                    """, (self.current_semester,))
                    prior_course_rows = cur.fetchall()

            # Group courses by (DefaultSemester, CourseGroup)
            # Find groups that have at least one course passed in prior semesters
            satisfied_group_keys = set()
            for code, sem, grp in prior_course_rows:
                if grp:
                    clean_c = clean_course_code(code)
                    if clean_c in all_passed_codes:
                        satisfied_group_keys.add((sem, grp.strip().upper()))

            prior_courses_filtered = set()
            for code, sem, grp in prior_course_rows:
                clean_c = clean_course_code(code)
                grp_key = (sem, grp.strip().upper()) if grp else None
                # If course belongs to a satisfied group, skip carrying it over
                if grp_key and grp_key in satisfied_group_keys:
                    continue
                prior_courses_filtered.add(clean_c)

            unpassed_prior_courses = prior_courses_filtered - all_passed_codes

            # Build rows for current semester default courses
            rows = []
            current_clean_codes = set()

            for course in current_courses:
                code, name, sem, cred, group = course
                clean_code = clean_course_code(code)
                current_clean_codes.add(clean_code)
                key = (clean_code, self.current_semester)
                info = enrollment_map.get(key)

                # Check prerequisites: MUST be passed in a semester PRIOR to current_semester
                prereqs = get_course_prerequisite(code)
                prereq_blocked = False
                for p in prereqs:
                    if clean_course_code(p) not in prior_passed_codes:
                        prereq_blocked = True
                        break

                enrolled = info is not None
                disabled = False
                status = "Not Enrolled"
                enrollment_id = info['id'] if info else None

                if info:
                    enrolled = True
                    disabled = True
                    status = format_enrollment_status(info['pass_status'], info['grade'], info['attempt'])
                else:
                    enrolled = False
                    disabled = False
                    status = "Not Enrolled"

                if prereq_blocked:
                    disabled = True
                    enrolled = False
                    status = "Prasyarat Belum Lulus"

                rows.append({
                    'code': code,
                    'name': name,
                    'credits': cred,
                    'enrolled': enrolled,
                    'status': status,
                    'enrollment_id': enrollment_id,
                    'disabled': disabled,
                    'is_carry': False,
                    'prereq_blocked': prereq_blocked,
                    'is_passed': clean_code in all_passed_codes,
                    'is_gagal': info and info['pass_status'] == 'GAGAL' if info else False
                })

            # Collect all course codes enrolled in current semester
            current_sem_enrolled_codes = set()
            for e in enrollments:
                s_num = get_semester_number_from_session(e[3])
                if s_num == self.current_semester:
                    current_sem_enrolled_codes.add(clean_course_code(e[2]))

            # Extra courses: unpassed prior courses + failed retakes + actively enrolled courses
            extra_codes = (unpassed_prior_courses | failed_codes | current_sem_enrolled_codes) - current_clean_codes

            courses_cache = get_cached_courses()
            for code_clean in sorted(extra_codes):
                info_cache = courses_cache.get(code_clean)
                if info_cache:
                    raw_code, name, sem, cred, grp = info_cache
                else:
                    raw_code, name, cred = code_clean, code_clean, 0

                key = (code_clean, self.current_semester)
                info = enrollment_map.get(key)
                enrolled = info is not None
                disabled = False

                prereqs = get_course_prerequisite(raw_code)
                prereq_blocked = False
                for p in prereqs:
                    if clean_course_code(p) not in prior_passed_codes:
                        prereq_blocked = True
                        break

                if info:
                    enrolled = True
                    disabled = True
                    status = format_enrollment_status(info['pass_status'], info['grade'], info['attempt'])
                else:
                    enrolled = False
                    disabled = False
                    status = "Not Enrolled"

                if prereq_blocked:
                    disabled = True
                    enrolled = False
                    status = "Prasyarat Belum Lulus"

                rows.append({
                    'code': raw_code,
                    'name': name,
                    'credits': cred,
                    'enrolled': enrolled,
                    'status': status,
                    'enrollment_id': info['id'] if info else None,
                    'disabled': disabled,
                    'is_carry': True,
                    'prereq_blocked': prereq_blocked,
                    'is_passed': code_clean in all_passed_codes,
                    'is_gagal': info and info['pass_status'] == 'GAGAL' if info else False
                })

            # CourseGroup Exclusivity Locking for current semester
            group_enrolled_map = {}
            for r in rows:
                c_info = courses_cache.get(clean_course_code(r['code']))
                grp = c_info[4] if c_info and len(c_info) >= 5 else None
                r['course_group'] = grp
                if r['enrolled'] and grp:
                    group_enrolled_map[grp] = clean_course_code(r['code'])

            for r in rows:
                grp = r.get('course_group')
                if grp and grp in group_enrolled_map:
                    if clean_course_code(r['code']) != group_enrolled_map[grp]:
                        r['enrolled'] = False
                        r['disabled'] = True
                        r['status'] = "Kumpulan Subjek Telah Dipilih"

            rows.sort(key=lambda x: (not x['is_carry'], clean_course_code(x['code'])))

            self.table.setRowCount(len(rows))
            self._updating_checkbox = True
            for i, row in enumerate(rows):
                cb = QCheckBox()
                cb.setChecked(row['enrolled'])
                cb.setEnabled(not row['disabled'])
                cb.clicked.connect(lambda checked, row_idx=i: self.on_checkbox_clicked(row_idx))
                self.table.setCellWidget(i, 0, cb)

                code_item = QTableWidgetItem(clean_course_code(row['code']))
                code_item.setData(Qt.UserRole, row['code'])
                self.table.setItem(i, 1, code_item)

                self.table.setItem(i, 2, QTableWidgetItem(row['name']))
                self.table.setItem(i, 3, QTableWidgetItem(str(row['credits'])))

                prereqs = get_course_prerequisite(row['code'])
                prereq_str = ", ".join([clean_course_code(p) for p in prereqs])
                self.table.setItem(i, 4, QTableWidgetItem(prereq_str))
                self.table.setItem(i, 5, QTableWidgetItem(row['status']))
            self._updating_checkbox = False

            # Update Study Plan Summarization View
            self.update_summary_and_study_plan(enrollments, all_passed_codes, failed_codes, current_courses)
        finally:
            QApplication.restoreOverrideCursor()

    def update_summary_and_study_plan(self, enrollments, passed_codes, failed_codes, current_courses):
        if not self.current_student:
            self.summary_group.setVisible(False)
            return

        self.summary_group.setVisible(True)

        cgpa = get_student_cgpa(self.current_student)
        max_cred = get_max_credits_by_cgpa(cgpa)

        # 1. Semester History Summary
        sem_history = {s: [] for s in range(1, 9)}
        for e in enrollments:
            s_num = get_semester_number_from_session(e[3])
            if s_num and 1 <= s_num <= 8:
                sem_history[s_num].append(e)

        self.history_table.setRowCount(8)
        for s in range(1, 9):
            e_list = sem_history[s]
            tot_cred = 0
            for e in e_list:
                with get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT CreditHours FROM Courses WHERE CourseCode = %s", (e[2],))
                        r = cur.fetchone()
                        if r: tot_cred += r[0]
            count = len(e_list)
            status_str = "Lengkap" if count > 0 and s < self.current_semester else ("Sesi Semasa" if s == self.current_semester else "Akan Datang")
            self.history_table.setItem(s - 1, 0, QTableWidgetItem(f"Semester {s}"))
            self.history_table.setItem(s - 1, 1, QTableWidgetItem(str(tot_cred)))
            self.history_table.setItem(s - 1, 2, QTableWidgetItem(str(count)))
            self.history_table.setItem(s - 1, 3, QTableWidgetItem(status_str))

        # 2. Current Semester Study Plan
        plan_rows = []
        planned_credits = 0

        # Mandatory Repeats
        for code in failed_codes:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT CourseName, CreditHours, DefaultSemester FROM Courses WHERE CourseCode = %s OR CourseCode LIKE %s LIMIT 1", (code, code + '-%'))
                    r = cur.fetchone()
                    if r:
                        c_name, c_cred, def_sem = r[0], r[1], r[2]
                    else:
                        c_name, c_cred, def_sem = code, 0, 1
            is_offered_now = (def_sem == self.current_semester or (self.current_semester % 2 == def_sem % 2))
            offered_text = "Dibuka Sesi Ini" if is_offered_now else "Tidak Dibuka Sesi Ini (Ditangguh ke Sem Seterusnya)"
            plan_rows.append({
                'sem': def_sem,
                'code': clean_course_code(code),
                'name': c_name,
                'credits': c_cred,
                'type': "Ulangan (Subjek Gagal)",
                'offered': offered_text,
                'is_offered': is_offered_now
            })
            if is_offered_now:
                planned_credits += c_cred

        # Regular Offered Courses
        for course in current_courses:
            code, name, sem, cred, group = course
            clean_code = clean_course_code(code)
            if clean_code in passed_codes or clean_code in failed_codes:
                continue
            plan_rows.append({
                'sem': sem,
                'code': clean_code,
                'name': name,
                'credits': cred,
                'type': "Subjek Semasa",
                'offered': "Dibuka Sesi Ini",
                'is_offered': True
            })
            planned_credits += cred

        self.plan_table.setRowCount(len(plan_rows))
        for i, row in enumerate(plan_rows):
            self.plan_table.setItem(i, 0, QTableWidgetItem(f"Sem {row['sem']}"))
            self.plan_table.setItem(i, 1, QTableWidgetItem(row['code']))
            self.plan_table.setItem(i, 2, QTableWidgetItem(row['name']))
            self.plan_table.setItem(i, 3, QTableWidgetItem(str(row['credits'])))
            self.plan_table.setItem(i, 4, QTableWidgetItem(row['type']))
            off_item = QTableWidgetItem(row['offered'])
            if not row['is_offered']:
                off_item.setForeground(Qt.darkYellow)
            else:
                off_item.setForeground(Qt.darkGreen)
            self.plan_table.setItem(i, 5, off_item)

        if planned_credits > max_cred:
            msg = f"⚠️ AMARAN: Jumlah kredit dicadangkan ({planned_credits} kredit) melebihi had maksimum CGPA ({max_cred} kredit). Penasihat disyorkan menggugurkan (drop) subjek elektif."
            self.summary_warning.setStyleSheet("color: red; font-weight: bold; padding: 5px;")
        else:
            msg = f"✅ Jumlah kredit dicadangkan: {planned_credits} / {max_cred} kredit (Had CGPA {cgpa:.2f}). Unjuran subjek teratur."
            self.summary_warning.setStyleSheet("color: green; font-weight: bold; padding: 5px;")
        self.summary_warning.setText(msg)

    def on_checkbox_clicked(self, row):
        cb = self.table.cellWidget(row, 0)
        if not isinstance(cb, QCheckBox) or not cb.isEnabled():
            return
        self.edit_enrollment_at_row(row)

    def on_cell_double_clicked(self, row, column):
        status_item = self.table.item(row, 5)
        status_text = status_item.text() if status_item else "Not Enrolled"
        if status_text == "Not Enrolled" or "Prasyarat" in status_text:
            return
        self.edit_enrollment_at_row(row)

    def edit_enrollment_at_row(self, row):
        code_item = self.table.item(row, 1)
        course_code = code_item.data(Qt.UserRole) if code_item and code_item.data(Qt.UserRole) else code_item.text()
        course_name = self.table.item(row, 2).text()

        existing = None
        enrollments = get_student_enrollments(self.current_student)
        for e in enrollments:
            sem_num = get_semester_number_from_session(e[3])
            if clean_course_code(e[2]) == clean_course_code(course_code) and sem_num == self.current_semester:
                existing = {
                    'id': e[0],
                    'session': e[3],
                    'attempt': e[4],
                    'grade': e[5],
                    'pass_status': e[6]
                }
                break

        dialog = EnrollmentEditDialog(self.current_student, course_code, course_name, self.current_semester, self.advisor_id, existing, self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                if existing:
                    update_enrollment(existing['id'], data['grade'], data['attempt'], data['session'], data['pass_status'])
                else:
                    add_enrollment(self.current_student, course_code, data['session'], data['attempt'], data['grade'], data['pass_status'])
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save enrollment: {str(e)}")
                self.refresh()
        else:
            self.refresh()

    def on_context_menu(self, pos: QPoint):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        course_code = self.table.item(row, 1).text()
        status_item = self.table.item(row, 5)
        status_text = status_item.text() if status_item else ""

        if status_text == "Not Enrolled" or status_text.startswith("Gagal - Ulang"):
            QMessageBox.information(self, "Info", "Student is not enrolled in this course.")
            return

        if "Prerequisite" in status_text:
            QMessageBox.information(self, "Info", "Cannot remove prerequisite-blocked course.")
            return

        if "Lulus" in status_text:
            QMessageBox.information(self, "Info", "Cannot remove a passed course.")
            return

        reply = QMessageBox.question(self, "Remove Enrollment",
                                     f"Remove enrollment for {course_code}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            current_session = f"2025/2026-SEM{self.current_semester}"
            enrollments = get_student_enrollments(self.current_student)
            for e in enrollments:
                if e[2] == course_code and e[3] == current_session:
                    try:
                        delete_enrollment(e[0])
                        self.refresh()
                    except Exception as ex:
                        QMessageBox.critical(self, "Error", f"Failed to remove: {str(ex)}")
                    break