from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QApplication
from PySide6.QtCore import Qt

class StartupSplashDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Memuatkan Sistem")
        self.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint)
        self.setFixedSize(450, 180)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e2e;
                border: 2px solid #45475a;
                border-radius: 12px;
            }
            QLabel#title {
                color: #cdd6f4;
                font-size: 16px;
                font-weight: bold;
            }
            QLabel#subtitle {
                color: #a6adc8;
                font-size: 13px;
            }
            QProgressBar {
                background-color: #313244;
                border-radius: 6px;
                height: 12px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #89b4fa;
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title_lbl = QLabel("Politeknik Student Course Management")
        title_lbl.setObjectName("title")
        title_lbl.setAlignment(Qt.AlignCenter)

        self.status_lbl = QLabel("Sistem Sedang Bermula... Memuatkan Data Pelajar & Subjek...")
        self.status_lbl.setObjectName("subtitle")
        self.status_lbl.setAlignment(Qt.AlignCenter)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0) # Indeterminate spinner pulse

        layout.addWidget(title_lbl)
        layout.addWidget(self.status_lbl)
        layout.addWidget(self.progress)
        self.setLayout(layout)

    def set_status(self, text):
        self.status_lbl.setText(text)
        QApplication.processEvents()
