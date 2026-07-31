from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView, QApplication
from PySide6.QtCore import Qt
from database.models import get_all_students, get_students_by_advisor, add_student, update_student, delete_student, sync_all_students_metrics
from ui.dialogs.add_dialog import AddStudentDialog

class StudentsTab(QWidget):
    def __init__(self, advisor_id=None, user_id=None, role=None, user_program=None):
        super().__init__()
        self.advisor_id = advisor_id
        self.user_id = user_id
        self.role = role
        self.user_program = user_program
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        self.table.cellChanged.connect(self.on_cell_changed)
        self.table.setSortingEnabled(True)

        layout = QVBoxLayout()
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ Add Student")
        add_btn.clicked.connect(self.add_row)
        delete_btn = QPushButton("🗑️ Delete Selected")
        delete_btn.clicked.connect(self.delete_row)
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self.refresh()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            QApplication.processEvents()
            sync_all_students_metrics()
            self.table.cellChanged.disconnect(self.on_cell_changed)
            self.table.blockSignals(True)
            self.table.setRowCount(0)

            header = self.table.horizontalHeader()
            if self.advisor_id:
                rows = get_students_by_advisor(self.advisor_id)
                self.table.setColumnCount(8)
                self.table.setHorizontalHeaderLabels(["Matric", "Name", "CGPA", "Class", "Total Credits", "Current Semester Credits", "Program", "Current Semester"])
                header.setSectionResizeMode(0, QHeaderView.Interactive)
                header.setSectionResizeMode(1, QHeaderView.Stretch)
                header.setSectionResizeMode(2, QHeaderView.Fixed)
                header.setSectionResizeMode(3, QHeaderView.Fixed)
                header.setSectionResizeMode(4, QHeaderView.Interactive)
                header.setSectionResizeMode(5, QHeaderView.Interactive)
                header.setSectionResizeMode(6, QHeaderView.Interactive)
                header.setSectionResizeMode(7, QHeaderView.Fixed)
                self.table.setColumnWidth(0, 130)
                self.table.setColumnWidth(2, 60)
                self.table.setColumnWidth(3, 80)
                self.table.setColumnWidth(7, 110)
            else:
                rows = get_all_students()
                self.table.setColumnCount(9)
                self.table.setHorizontalHeaderLabels(["Matric", "Name", "CGPA", "Class", "Total Credits", "Current Semester Credits", "Advisor", "Program", "Current Semester"])
                header.setSectionResizeMode(0, QHeaderView.Interactive)
                header.setSectionResizeMode(1, QHeaderView.Stretch)
                header.setSectionResizeMode(2, QHeaderView.Fixed)
                header.setSectionResizeMode(3, QHeaderView.Fixed)
                header.setSectionResizeMode(4, QHeaderView.Interactive)
                header.setSectionResizeMode(5, QHeaderView.Interactive)
                header.setSectionResizeMode(6, QHeaderView.Interactive)
                header.setSectionResizeMode(7, QHeaderView.Interactive)
                header.setSectionResizeMode(8, QHeaderView.Fixed)
                self.table.setColumnWidth(0, 130)
                self.table.setColumnWidth(2, 60)
                self.table.setColumnWidth(3, 80)
                self.table.setColumnWidth(8, 110)

            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                self.table.setItem(i, 0, QTableWidgetItem(row[0] if row[0] else ""))
                self.table.setItem(i, 1, QTableWidgetItem(row[1] if row[1] else ""))
                self.table.setItem(i, 2, QTableWidgetItem(str(row[2]) if row[2] is not None else "0.0"))
                self.table.setItem(i, 3, QTableWidgetItem(row[3] if row[3] else ""))
                self.table.setItem(i, 4, QTableWidgetItem(str(row[4]) if row[4] is not None else "0"))
                self.table.setItem(i, 5, QTableWidgetItem(str(row[5]) if row[5] is not None else "0"))

                if self.advisor_id:
                    self.table.setItem(i, 6, QTableWidgetItem(row[6] if row[6] else ""))
                    self.table.setItem(i, 7, QTableWidgetItem(str(row[7]) if row[7] is not None else "1"))
                else:
                    self.table.setItem(i, 6, QTableWidgetItem(row[6] if row[6] else "Unassigned"))
                    self.table.setItem(i, 7, QTableWidgetItem(row[7] if row[7] else ""))
                    self.table.setItem(i, 8, QTableWidgetItem(str(row[8]) if row[8] is not None else "1"))

            self.table.blockSignals(False)
            self.table.cellChanged.connect(self.on_cell_changed)
        finally:
            QApplication.restoreOverrideCursor()

    def on_cell_changed(self, row, col):
        # Allowed columns: Name(1), CGPA(2), Class(3), Program(6 for advisor / 7 for admin), CurrentSemester(7 / 8)
        if self.advisor_id:
            editable_cols = [1,2,3,6,7]
        else:
            editable_cols = [1,2,3,7,8]
        if col not in editable_cols:
            return
        matric_item = self.table.item(row, 0)
        if not matric_item:
            return
        matric = matric_item.text().strip()
        if not matric:
            return

        name = self.table.item(row, 1).text().strip() if self.table.item(row, 1) else ""
        cgpa_str = self.table.item(row, 2).text().strip() if self.table.item(row, 2) else "0.0"
        class_name = self.table.item(row, 3).text().strip() if self.table.item(row, 3) else ""

        try:
            cgpa = float(cgpa_str) if cgpa_str else 0.0
        except ValueError:
            cgpa = 0.0

        # Get program and current_semester based on role
        if self.advisor_id:
            program = self.table.item(row, 6).text().strip() if self.table.item(row, 6) else None
            current_semester_str = self.table.item(row, 7).text().strip() if self.table.item(row, 7) else "1"
        else:
            program = self.table.item(row, 7).text().strip() if self.table.item(row, 7) else None
            current_semester_str = self.table.item(row, 8).text().strip() if self.table.item(row, 8) else "1"
        try:
            current_semester = int(current_semester_str) if current_semester_str else 1
        except ValueError:
            current_semester = 1

        try:
            update_student(matric, name, cgpa, class_name, self.advisor_id if self.advisor_id else None, program, current_semester)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Update failed: {str(e)}")
            self.refresh()

    def add_row(self):
        dialog = AddStudentDialog(current_user_id=self.user_id, current_role=self.role, user_program=self.user_program)
        if dialog.exec():
            data = dialog.get_data()
            if not data['matric'] or not data['name']:
                QMessageBox.warning(self, "Error", "Matric and Name are required.")
                return
            if data['advisor_id'] is None:
                QMessageBox.warning(self, "Error", "Please select an Academic Advisor.")
                return
            try:
                add_student(data['matric'], data['name'], data['cgpa'], data['class'], data['advisor_id'], data['program'], data['current_semester'])
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Add failed: {str(e)}")

    def delete_row(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "No selection", "Select a row to delete.")
            return
        matric = self.table.item(selected, 0).text()
        reply = QMessageBox.question(self, "Confirm", f"Delete student {matric}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                delete_student(matric)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Delete failed: {str(e)}")