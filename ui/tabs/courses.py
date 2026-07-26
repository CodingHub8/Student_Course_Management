from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView,
                               QDialog, QListWidget, QScrollArea, QGroupBox, QLabel)
from PySide6.QtCore import Qt
from database.models import (get_all_courses, add_course, update_course, delete_course,
                             get_course_prerequisite, add_prerequisite, delete_prerequisite, get_prereq_id)
from ui.dialogs.add_dialog import AddCourseDialog

class ManagePrereqDialog(QDialog):
    def __init__(self, course_code, parent=None):
        super().__init__(parent)
        self.course_code = course_code
        self.setWindowTitle(f"Manage Prerequisites for {course_code}")
        self.setFixedSize(400, 300)
        layout = QVBoxLayout()
        self.list_widget = QListWidget()
        self.refresh_list()
        layout.addWidget(self.list_widget)
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self.add_prereq)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_prereq)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def refresh_list(self):
        self.list_widget.clear()
        prereqs = get_course_prerequisite(self.course_code)
        for p in prereqs:
            self.list_widget.addItem(p)

    def add_prereq(self):
        from ui.dialogs.add_dialog import AddPrereqDialog
        dialog = AddPrereqDialog(preselected_course=self.course_code)
        if dialog.exec():
            data = dialog.get_data()
            try:
                add_prerequisite(data['course'], data['prereq'])
                self.refresh_list()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add prerequisite: {str(e)}")

    def remove_prereq(self):
        selected = self.list_widget.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "No selection", "Select a prerequisite to remove.")
            return
        prereq_code = self.list_widget.item(selected).text()
        prereq_id = get_prereq_id(self.course_code, prereq_code)
        if prereq_id:
            try:
                delete_prerequisite(prereq_id)
                self.refresh_list()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to remove: {str(e)}")
        else:
            QMessageBox.warning(self, "Error", "Could not find that prerequisite in database.")


class CoursesTab(QWidget):
    def __init__(self, user_id=None, role=None, cohort=None, user_program=None):
        super().__init__()
        self.user_id = user_id
        self.role = role
        self.cohort = cohort
        self.user_program = user_program
        self.selected_course = None

        self.main_layout = QVBoxLayout()

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("➕ Add Course")
        self.add_btn.clicked.connect(self.add_row)
        self.delete_btn = QPushButton("🗑️ Delete Selected")
        self.delete_btn.clicked.connect(self.delete_row)
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch()
        self.main_layout.addLayout(btn_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_area.setWidget(self.scroll_widget)
        self.main_layout.addWidget(self.scroll_area)

        self.setLayout(self.main_layout)

        self.tables = {}
        self.refresh()

    def refresh(self):
        self.tables.clear()
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        rows = get_all_courses()  # (code, name, semester, credits, cohort, program, course_group)
        sem_dict = {}
        for row in rows:
            if len(row) < 7:
                continue
            code, name, sem, cred, cohort, program, group = row[:7]
            if sem not in sem_dict:
                sem_dict[sem] = []
            sem_dict[sem].append({
                'code': code,
                'name': name,
                'credits': cred,
                'cohort': cohort,
                'program': program,
                'course_group': group,
                'prereqs': get_course_prerequisite(code)
            })

        for semester in sorted(sem_dict.keys()):
            group_box = QGroupBox(f"Semester {semester}")
            group_layout = QVBoxLayout()

            table = QTableWidget()
            table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
            table.setSortingEnabled(True)
            table.setColumnCount(6)
            table.setHorizontalHeaderLabels(["Code", "Name", "Credits", "Cohort", "Program", "Prerequisites"])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            table.setProperty("semester", semester)

            table.blockSignals(True)

            courses = sem_dict[semester]
            table.setRowCount(len(courses) + 1)
            # Calculate total credits, handling course groups
            group_credits = {}
            core_total = 0
            for course in courses:
                group = course['course_group']
                if group is None:
                    core_total += course['credits']
                else:
                    if group not in group_credits:
                        group_credits[group] = []
                    group_credits[group].append(course['credits'])

            # For each group, add the max credit (student picks one)
            group_total = 0
            for g, credits in group_credits.items():
                group_total += max(credits)  # assume student takes highest credit option

            total_credits = core_total + group_total

            for i, course in enumerate(courses):
                table.setItem(i, 0, QTableWidgetItem(course['code'].removesuffix("-1")))
                table.setItem(i, 1, QTableWidgetItem(course['name']))
                table.setItem(i, 2, QTableWidgetItem(str(course['credits'])))
                table.setItem(i, 3, QTableWidgetItem(course['cohort'] if course['cohort'] else ""))
                table.setItem(i, 4, QTableWidgetItem(course['program'] if course['program'] else ""))
                prereq_str = ", ".join(course['prereqs']) if course['prereqs'] else ""
                table.setItem(i, 5, QTableWidgetItem(prereq_str))

            total_row = len(courses)
            total_name_item = QTableWidgetItem("Total")
            total_name_item.setFlags(Qt.ItemIsEnabled)
            table.setItem(total_row, 1, total_name_item)

            total_cred_item = QTableWidgetItem(str(total_credits))
            total_cred_item.setFlags(Qt.ItemIsEnabled)
            table.setItem(total_row, 2, total_cred_item)

            for col in [0, 3, 4, 5]:
                item = QTableWidgetItem("")
                item.setFlags(Qt.ItemIsEnabled)
                table.setItem(total_row, col, item)

            for col in range(table.columnCount()):
                item = table.item(total_row, col)
                if item:
                    item.setBackground(Qt.lightGray)

            table.blockSignals(False)

            table.cellChanged.connect(self.on_cell_changed)
            table.cellDoubleClicked.connect(self.on_cell_double_clicked)
            table.itemClicked.connect(self.on_item_clicked)

            group_layout.addWidget(table)
            group_box.setLayout(group_layout)
            group_box.setMinimumHeight(200)
            self.scroll_layout.addWidget(group_box)

            self.tables[semester] = table

        if not self.tables:
            label = QLabel("No courses found. Add a course to get started.")
            label.setAlignment(Qt.AlignCenter)
            self.scroll_layout.addWidget(label)

    def on_cell_changed(self, row, col):
        # unchanged – same as before
        table = self.sender()
        if not isinstance(table, QTableWidget):
            return
        semester = table.property("semester")
        if semester is None:
            return

        if row == table.rowCount() - 1:
            return
        if col == 5:
            return

        code_item = table.item(row, 0)
        if not code_item:
            return
        code = code_item.text().strip()
        if not code:
            return

        name = table.item(row, 1).text().strip() if table.item(row, 1) else ""
        cred_str = table.item(row, 2).text().strip() if table.item(row, 2) else "0"
        cohort = table.item(row, 3).text().strip().upper() if table.item(row, 3) else None
        program = table.item(row, 4).text().strip().upper() if table.item(row, 4) else None

        try:
            cred = int(cred_str) if cred_str else 0
        except ValueError:
            cred = 0

        try:
            update_course(code, name, semester, cred, cohort, program)
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Update failed: {str(e)}")
            self.refresh()

    def on_cell_double_clicked(self, row, col):
        table = self.sender()
        if not isinstance(table, QTableWidget):
            return
        if row == table.rowCount() - 1:
            return
        if col == 5:
            code_item = table.item(row, 0)
            if code_item:
                course_code = code_item.text()
                dialog = ManagePrereqDialog(course_code, self)
                dialog.exec()
                self.refresh()

    def on_item_clicked(self, item):
        table = self.sender()
        if not isinstance(table, QTableWidget):
            return
        row = item.row()
        if row == table.rowCount() - 1:
            return
        code_item = table.item(row, 0)
        if code_item:
            self.selected_course = code_item.text()

    def add_row(self):
        dialog = AddCourseDialog(current_user_id=self.user_id, current_role=self.role,
                                 user_cohort=self.cohort, user_program=self.user_program)
        if dialog.exec():
            data = dialog.get_data()
            try:
                final_code = add_course(data['code'], data['name'], data['semester'], data['credits'],
                                        data['cohort'], data['program'], data.get('course_group', None))
                if data['prerequisites']:
                    for prereq in data['prerequisites']:
                        try:
                            add_prerequisite(final_code, prereq)
                        except Exception as e:
                            QMessageBox.warning(self, "Warning", f"Failed to add prerequisite '{prereq}': {str(e)}")
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Add failed: {str(e)}")
                self.refresh()

    def delete_row(self):
        if not self.selected_course:
            QMessageBox.warning(self, "No selection", "Please click on a course row to select it.")
            return
        code = self.selected_course
        reply = QMessageBox.question(self, "Confirm", f"Delete course {code}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                delete_course(code)
                self.selected_course = None
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Delete failed: {str(e)}")