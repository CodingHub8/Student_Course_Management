from PySide6.QtWidgets import QMainWindow, QTabWidget, QMenuBar, QMessageBox, QFileDialog
from ui.tabs.enrollments import EnrollmentsTab
from ui.tabs.courses import CoursesTab
from ui.tabs.students import StudentsTab
from utils.backup import export_backup, import_backup

class MainWindow(QMainWindow):
    def __init__(self, user_id, role, cohort, program):
        super().__init__()
        self.user_id = user_id
        self.role = role
        self.cohort = cohort
        self.program = program
        self.setWindowTitle("Student Planner – Academic Advisor System")
        self.setGeometry(100, 100, 1200, 700)

        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        export_action = file_menu.addAction("Export Backup")
        export_action.triggered.connect(self.export_backup)
        import_action = file_menu.addAction("Import Data")
        import_action.triggered.connect(self.import_data)
        file_menu.addSeparator()
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        is_admin = bool(self.role and str(self.role).lower() in ('admin', 'system administrator'))
        if is_admin:
            admin_menu = menubar.addMenu("Admin")
            change_pw_action = admin_menu.addAction("Change User Password")
            change_pw_action.triggered.connect(self.open_change_password_dialog)

        self.tabs = QTabWidget()
        advisor_id = None if is_admin else self.user_id

        self.students_tab = StudentsTab(advisor_id=advisor_id, user_id=self.user_id, role=self.role, user_program=program)
        self.enroll_tab = EnrollmentsTab(advisor_id=advisor_id)
        self.courses_tab = CoursesTab(user_id=self.user_id, role=self.role, cohort=self.cohort, user_program=program)

        self.tabs.addTab(self.students_tab, "Students")
        self.tabs.addTab(self.enroll_tab, "Enrollments")
        self.tabs.addTab(self.courses_tab, "Courses")

        self.setCentralWidget(self.tabs)

    def import_data(self):
        from ui.dialogs.import_dialog import ImportDialog
        dialog = ImportDialog(self)
        if dialog.exec():
            self.students_tab.refresh()
            self.enroll_tab.refresh()
            self.courses_tab.refresh()

    def export_backup(self):
        from utils.export_import import export_to_csv, export_to_xlsx, export_to_pdf, export_to_docx
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Data",
            "student_records",
            "PDF Report (*.pdf);;CSV Spreadsheet (*.csv);;Excel Workbook (*.xlsx);;Word Document (*.docx);;SQL Database Backup (*.sql)"
        )
        if file_path:
            try:
                ext = file_path.split('.')[-1].lower()
                if ext == 'csv':
                    export_to_csv(file_path)
                elif ext == 'xlsx':
                    export_to_xlsx(file_path)
                elif ext == 'pdf':
                    export_to_pdf(file_path)
                elif ext == 'docx':
                    export_to_docx(file_path)
                else:
                    export_backup(file_path)
                QMessageBox.information(self, "Success", f"Data exported successfully to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")

    def import_backup(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Backup File", "", "SQL files (*.sql)")
        if file_path:
            reply = QMessageBox.question(self, "Confirm", "This will overwrite all current data. Continue?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                try:
                    import_backup(file_path)
                    QMessageBox.information(self, "Success", "Data restored successfully.")
                    self.students_tab.refresh()
                    self.enroll_tab.refresh()
                    self.courses_tab.refresh()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Import failed: {str(e)}")

    def open_change_password_dialog(self):
        from ui.dialogs.change_password_dialog import ChangePasswordDialog
        dialog = ChangePasswordDialog(self)
        dialog.exec()