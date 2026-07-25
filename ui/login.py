from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox
from database.models import validate_user
from ui.register import RegisterDialog

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login")
        self.setFixedSize(300, 200)

        layout = QVBoxLayout()
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("IC Number")
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Password")
        self.password_edit.setEchoMode(QLineEdit.Password)

        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.attempt_login)

        register_btn = QPushButton("Register New Advisor")
        register_btn.clicked.connect(self.open_register)

        layout.addWidget(QLabel("Enter your credentials:"))
        layout.addWidget(self.username_edit)
        layout.addWidget(self.password_edit)
        layout.addWidget(login_btn)
        layout.addWidget(register_btn)

        self.setLayout(layout)
        self.user_id = None
        self.role = None
        self.cohort = None
        self.program = None

    def attempt_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        user = validate_user(username, password)
        if user:
            self.user_id = user['user_id']
            self.role = user['role']
            self.cohort = user['cohort']
            self.program = user['program']
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Invalid IC or password.")

    def open_register(self):
        self.setEnabled(False)
        dialog = RegisterDialog(self)
        dialog.exec()
        self.setEnabled(True)
        self.raise_()
        self.activateWindow()

    def get_user_id(self):
        return self.user_id

    def get_role(self):
        return self.role

    def get_cohort(self):
        return self.cohort

    def get_program(self):
        return self.program