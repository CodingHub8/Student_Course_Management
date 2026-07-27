from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QMessageBox, QHBoxLayout, QComboBox
from database.models import register_user

class RegisterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Register New Advisor")
        self.setFixedSize(450, 400)
        layout = QVBoxLayout()
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Full Name")
        self.ic_edit = QLineEdit()
        self.ic_edit.setPlaceholderText("e.g., 010203010203")
        self.cohort_edit = QLineEdit()
        self.cohort_edit.setPlaceholderText("e.g., SESI 1 2025/2026")
        self.program_combo = QComboBox()
        self.program_combo.addItems(["DEE", "DDT", "DET", "Other"])  # Add more as needed

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("Min 8 characters")
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(QLineEdit.Password)
        self.confirm_edit.setPlaceholderText("Confirm password")

        form.addRow("Full Name:", self.name_edit)
        form.addRow("IC Number:", self.ic_edit)
        form.addRow("Cohort:", self.cohort_edit)
        form.addRow("Program:", self.program_combo)
        form.addRow("Password:", self.password_edit)
        form.addRow("Confirm Password:", self.confirm_edit)

        btn_layout = QHBoxLayout()
        register_btn = QPushButton("Register")
        register_btn.clicked.connect(self.register)
        back_btn = QPushButton("← Back to Login")
        back_btn.clicked.connect(self.go_back)

        btn_layout.addWidget(register_btn)
        btn_layout.addWidget(back_btn)

        layout.addLayout(form)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def register(self):
        name = self.name_edit.text().strip()
        ic = self.ic_edit.text().strip()
        cohort = self.cohort_edit.text().strip().upper()
        program = self.program_combo.currentText().strip().upper()
        password = self.password_edit.text().strip()
        confirm = self.confirm_edit.text().strip()

        if not name or not ic or not password or not cohort or not program:
            QMessageBox.warning(self, "Error", "All fields are required.")
            return
        if len(password) < 8:
            QMessageBox.warning(self, "Error", "Password must be at least 8 characters.")
            return
        if password != confirm:
            QMessageBox.warning(self, "Error", "Passwords do not match.")
            return

        success = register_user(ic, password, name, cohort, program)
        if success:
            QMessageBox.information(self, "Success", "Registration successful! You can now log in.")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "This IC number is already registered. Please log in.")

    def go_back(self):
        self.reject()