import sys
from PySide6.QtWidgets import QApplication
from database.init_db import init_database
from ui.login import LoginDialog
from ui.main_window import MainWindow

def main():
    init_database()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    login = LoginDialog()
    if login.exec() == LoginDialog.Accepted:
        app.setQuitOnLastWindowClosed(True)
        user_id = login.get_user_id()
        role = login.get_role()
        cohort = login.get_cohort()
        program = login.get_program()

        from ui.dialogs.startup_splash import StartupSplashDialog
        from database.models import sync_all_students_metrics, get_cached_courses

        splash = StartupSplashDialog()
        splash.show()
        QApplication.processEvents()

        splash.set_status("Memuatkan Data Subjek & Matriks Pelajar...")
        get_cached_courses()
        sync_all_students_metrics()

        window = MainWindow(user_id, role, cohort, program)
        window.show()
        splash.close()
        sys.exit(app.exec())
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()