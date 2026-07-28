import sys
import ctypes
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThread, Signal, QEventLoop
from database.init_db import init_database
from database.connection import close_pool
from ui.login import LoginDialog
from ui.main_window import MainWindow
from utils.resource import get_app_icon

class StartupSyncWorker(QThread):
    status_signal = Signal(str)
    finished_signal = Signal()

    def run(self):
        from database.models import sync_all_students_metrics, get_cached_courses
        self.status_signal.emit("Memuatkan Data Subjek...")
        get_cached_courses()
        self.status_signal.emit("Menyegerakkan Matriks Pelajar...")
        sync_all_students_metrics()
        self.finished_signal.emit()

def main():
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Politeknik.StudentCourseManagement.App.1.0")
    except Exception:
        pass

    init_database()
    app = QApplication(sys.argv)
    app.setWindowIcon(get_app_icon())
    app.setQuitOnLastWindowClosed(False)

    login = LoginDialog()
    if login.exec() == LoginDialog.Accepted:
        app.setQuitOnLastWindowClosed(True)
        user_id = login.get_user_id()
        role = login.get_role()
        cohort = login.get_cohort()
        program = login.get_program()

        from ui.dialogs.startup_splash import StartupSplashDialog

        splash = StartupSplashDialog()
        splash.show()
        QApplication.processEvents()

        loop = QEventLoop()
        worker = StartupSyncWorker()
        worker.status_signal.connect(splash.set_status)
        worker.finished_signal.connect(loop.quit)
        worker.start()
        loop.exec()

        window = MainWindow(user_id, role, cohort, program)
        window.show()
        splash.close()
        
        ret = app.exec()
        close_pool()
        sys.exit(ret)
    else:
        close_pool()
        sys.exit(0)

if __name__ == "__main__":
    main()