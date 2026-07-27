from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QComboBox,
                                QLineEdit, QPushButton, QMessageBox, QLabel)
from database.models import get_all_users, update_user_password

class ChangePasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Admin - Change User Password")
        self.setFixedSize(400, 240)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; color: #cdd6f4; }
            QLabel { color: #cdd6f4; font-size: 13px; font-weight: bold; }
            QLineEdit, QComboBox {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 6px;
                color: #cdd6f4;
            }
            QPushButton {
                background-color: #89b4fa;
                color: #11111b;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #b4befe; }
        """)

        layout = QVBoxLayout()
        form = QFormLayout()

        self.user_combo = QComboBox()
        self.users = get_all_users()
        for u in self.users:
            uid, name, role, username, program = u
            display = f"{name or username} ({role}) - {username}"
            self.user_combo.addItem(display, userData=uid)

        self.new_pw = QLineEdit()
        self.new_pw.setEchoMode(QLineEdit.Password)
        self.new_pw.setPlaceholderText("Enter new password")

        self.confirm_pw = QLineEdit()
        self.confirm_pw.setEchoMode(QLineEdit.Password)
        self.confirm_pw.setPlaceholderText("Confirm new password")

        form.addRow("Select User:", self.user_combo)
        form.addRow("New Password:", self.new_pw)
        form.addRow("Confirm Password:", self.confirm_pw)

        btn = QPushButton("Update Password")
        btn.clicked.connect(self.save)

        layout.addLayout(form)
        layout.addWidget(btn)
        self.setLayout(layout)

    def save(self):
        user_id = self.user_combo.currentData()
        pw = self.new_pw.text().strip()
        cpw = self.confirm_pw.text().strip()

        if not pw or not cpw:
            QMessageBox.warning(self, "Error", "All password fields are required.")
            return
        if len(pw) < 8:
            QMessageBox.warning(self, "Error", "Password must be at least 8 characters.")
            return
        if pw != cpw:
            QMessageBox.warning(self, "Error", "Passwords do not match.")
            return

        success = update_user_password(user_id, pw)
        if success:
            QMessageBox.information(self, "Success", "Password updated successfully!")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to update password.")
