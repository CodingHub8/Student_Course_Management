from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView
from PySide6.QtCore import Qt
from database.models import get_all_students, get_students_by_advisor, add_student, update_student, delete_student
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

    def refresh(self):
        # Disconnect signal and block signals during population
        self.table.cellChanged.disconnect(self.on_cell_changed)
        self.table.blockSignals(True)

        # Clear table
        self.table.setRowCount(0)

        # Set columns based on role
        if self.advisor_id:
            rows = get_students_by_advisor(self.advisor_id)
            # rows: (matric, name, cgpa, class, total_cred, current_cred, program)
            self.table.setColumnCount(8)
            self.table.setHorizontalHeaderLabels(
                ["Matric", "Name", "CGPA", "Class", "Total Credits", "Current Credits", "Program", "Current Semester"])
        else:
            rows = get_all_students()
            # rows: (matric, name, cgpa, class, total_cred, current_cred, advisor_name, program)
            self.table.setColumnCount(9)
            self.table.setHorizontalHeaderLabels(["Matric", "Name", "CGPA", "Class", "Total Credits", "Current Credits", "Advisor", "Program", "Current Semester"])

        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            # Matric (index 0)
            self.table.setItem(i, 0, QTableWidgetItem(row[0] if row[0] else ""))
            # Name (index 1)
            self.table.setItem(i, 1, QTableWidgetItem(row[1] if row[1] else ""))
            # CGPA (index 2)
            self.table.setItem(i, 2, QTableWidgetItem(str(row[2]) if row[2] is not None else "0.0"))
            # Class (index 3)
            self.table.setItem(i, 3, QTableWidgetItem(row[3] if row[3] else ""))
            # Total Credits (index 4)
            self.table.setItem(i, 4, QTableWidgetItem(str(row[4]) if row[4] is not None else "0"))
            # Current Credits (index 5)
            self.table.setItem(i, 5, QTableWidgetItem(str(row[5]) if row[5] is not None else "0"))

            if self.advisor_id:
                # Program is at index 6
                self.table.setItem(i, 6, QTableWidgetItem(row[6] if row[6] else ""))
            else:
                # For admin, advisor_name at index 6, program at index 7
                self.table.setItem(i, 6, QTableWidgetItem(row[6] if row[6] else "Unassigned"))
                self.table.setItem(i, 7, QTableWidgetItem(row[7] if row[7] else ""))
                self.table.setItem(i, 8, QTableWidgetItem(str(row[8]) if row[8] else "1"))

        # Unblock signals and reconnect
        self.table.blockSignals(False)
        self.table.resizeColumnsToContents()
        self.table.cellChanged.connect(self.on_cell_changed)

    def on_cell_changed(self, row, col):
        # Only allow editing of Name, CGPA, Class (cols 1,2,3)
        if col not in [1,2,3]:
            return
        matric_item = self.table.item(row, 0)
        if not matric_item:
            return
        matric = matric_item.text().strip()
        if not matric:
            # If Matric is empty, ignore – cannot update without identifier
            return

        name = self.table.item(row, 1).text().strip() if self.table.item(row, 1) else ""
        cgpa_str = self.table.item(row, 2).text().strip() if self.table.item(row, 2) else "0.0"
        class_name = self.table.item(row, 3).text().strip() if self.table.item(row, 3) else ""

        try:
            cgpa = float(cgpa_str) if cgpa_str else 0.0
        except ValueError:
            cgpa = 0.0

        # For advisor, keep existing program; for admin we could preserve, but we pass None to keep existing
        try:
            update_student(matric, name, cgpa, class_name, self.advisor_id if self.advisor_id else None, None)
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
                add_student(data['matric'], data['name'], data['cgpa'], data['class'], data['advisor_id'], data['program'])
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