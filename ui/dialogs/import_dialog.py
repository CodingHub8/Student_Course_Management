import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                               QFileDialog, QComboBox, QTableWidget, QTableWidgetItem,
                               QTextEdit, QLabel, QMessageBox, QHeaderView, QProgressBar)
from PySide6.QtCore import Qt, QThread, Signal
import pandas as pd
from utils.importer import parse_file, get_excel_sheet_names
from utils.importer import import_courses, import_prerequisites, import_students, import_enrollments, auto_map_columns

class ImportWorker(QThread):
    progress = Signal(int)
    log = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, file_path, import_type, column_mapping, sheet_name=None):
        super().__init__()
        self.file_path = file_path
        self.import_type = import_type
        self.column_mapping = column_mapping
        self.sheet_name = sheet_name

    def run(self):
        try:
            # Parse the file with sheet selection
            df = parse_file(self.file_path, sheet_name=self.sheet_name)
            if df is None or df.empty:
                self.finished.emit(False, "No data parsed from file.")
                return

            # Apply column mapping (renaming)
            for db_col, file_col in self.column_mapping.items():
                if file_col and file_col in df.columns:
                    df.rename(columns={file_col: db_col}, inplace=True)

            # Select only needed columns based on import_type
            if self.import_type == "Courses":
                imported = import_courses(df, ['CourseCode', 'CourseName', 'DefaultSemester', 'CreditHours'])
            elif self.import_type == "Prerequisites":
                imported = import_prerequisites(df, ['CourseCode', 'PrereqCode'])
            elif self.import_type == "Students":
                imported = import_students(df, ['MatricNo', 'Name', 'CurrentCGPA'])
            elif self.import_type == "Enrollments":
                imported = import_enrollments(df, ['StudentID', 'CourseCode', 'SemesterSession', 'AttemptType', 'Grade'])
            else:  # All
                imported = {}
                imported['Students'] = import_students(df, ['MatricNo', 'Name', 'CurrentCGPA'])
                imported['Courses'] = import_courses(df, ['CourseCode', 'CourseName', 'DefaultSemester', 'CreditHours'])
                imported['Prerequisites'] = import_prerequisites(df, ['CourseCode', 'PrereqCode'])
                imported['Enrollments'] = import_enrollments(df, ['StudentID', 'CourseCode', 'SemesterSession', 'AttemptType', 'Grade'])

            self.finished.emit(True, "Import completed successfully.")

        except Exception as e:
            self.finished.emit(False, f"Error during import: {str(e)}")


class ImportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Data")
        self.setGeometry(200, 200, 900, 700)

        layout = QVBoxLayout()

        # File selection
        file_layout = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)

        # Sheet selection (hidden by default)
        sheet_layout = QHBoxLayout()
        self.sheet_label = QLabel("Sheet:")
        self.sheet_label.setVisible(False)
        self.sheet_combo = QComboBox()
        self.sheet_combo.setVisible(False)
        self.sheet_combo.currentIndexChanged.connect(self.preview_file)
        sheet_layout.addWidget(self.sheet_label)
        sheet_layout.addWidget(self.sheet_combo)
        sheet_layout.addStretch()
        layout.addLayout(sheet_layout)

        # Import type selection
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Import Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["All", "Courses", "Prerequisites", "Students", "Enrollments"])
        self.type_combo.currentIndexChanged.connect(self.update_preview)
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        layout.addLayout(type_layout)

        # Preview table
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(0)
        self.preview_table.setRowCount(0)
        layout.addWidget(QLabel("Preview (first 5 rows):"))
        layout.addWidget(self.preview_table)

        # Log area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        layout.addWidget(QLabel("Log:"))
        layout.addWidget(self.log_text)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Buttons
        btn_layout = QHBoxLayout()
        import_btn = QPushButton("Import")
        import_btn.clicked.connect(self.start_import)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(import_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.current_df = None
        self.file_path = None
        self.sheet_names = []

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select File to Import",
            "", "All Files (*);;CSV Files (*.csv);;Excel Files (*.xlsx *.xls);;PDF Files (*.pdf);;Text Files (*.txt)"
        )
        if file_path:
            self.file_path = file_path
            self.file_label.setText(os.path.basename(file_path))
            # Check for Excel sheets
            if file_path.lower().endswith(('.xlsx', '.xls')):
                try:
                    self.sheet_names = get_excel_sheet_names(file_path)
                    if len(self.sheet_names) > 1:
                        self.sheet_combo.clear()
                        self.sheet_combo.addItems(self.sheet_names)
                        self.sheet_combo.setVisible(True)
                        self.sheet_label.setVisible(True)
                    else:
                        self.sheet_combo.setVisible(False)
                        self.sheet_label.setVisible(False)
                        # If only one sheet, we still pass it (optional)
                except Exception as e:
                    self.log_text.append(f"Error reading Excel sheets: {str(e)}")
                    self.sheet_combo.setVisible(False)
                    self.sheet_label.setVisible(False)
            else:
                self.sheet_combo.setVisible(False)
                self.sheet_label.setVisible(False)
            self.preview_file()

    def preview_file(self):
        if not self.file_path:
            return
        try:
            sheet = None
            if self.sheet_combo.isVisible() and self.sheet_combo.currentIndex() >= 0:
                sheet = self.sheet_combo.currentText()
            df = parse_file(self.file_path, sheet_name=sheet)
            if df is None or df.empty:
                self.log_text.append("Error: No data parsed from file.")
                return
            self.current_df = df
            self.update_preview()
        except Exception as e:
            self.log_text.append(f"Error parsing file: {str(e)}")

    def update_preview(self):
        if self.current_df is None:
            return
        df = self.current_df
        preview = df.head(5)
        self.preview_table.setRowCount(len(preview))
        self.preview_table.setColumnCount(len(preview.columns))
        self.preview_table.setHorizontalHeaderLabels(preview.columns)
        for i, row in preview.iterrows():
            for j, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                self.preview_table.setItem(i, j, item)
        self.preview_table.resizeColumnsToContents()

        # Auto-map columns
        import_type = self.type_combo.currentText()
        mapping = auto_map_columns(df.columns.tolist(), import_type)
        if mapping:
            self.log_text.append(f"Auto-mapped columns: {mapping}")
        else:
            self.log_text.append("Could not auto-map columns. Please check column names.")

    def start_import(self):
        if not self.file_path:
            QMessageBox.warning(self, "Error", "Please select a file first.")
            return

        if self.current_df is None:
            QMessageBox.warning(self, "Error", "No data preview available.")
            return

        import_type = self.type_combo.currentText()
        mapping = auto_map_columns(self.current_df.columns.tolist(), import_type)
        if not mapping:
            reply = QMessageBox.question(self, "Mapping Incomplete",
                                         "Auto-mapping failed. Do you want to continue with partial mapping?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return

        # Get selected sheet
        sheet = None
        if self.sheet_combo.isVisible():
            sheet = self.sheet_combo.currentText()

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        self.worker = ImportWorker(self.file_path, import_type, mapping, sheet_name=sheet)
        self.worker.log.connect(self.log_text.append)
        self.worker.finished.connect(self.on_import_finished)
        self.worker.start()

    def on_import_finished(self, success, message):
        self.progress_bar.setVisible(False)
        if success:
            QMessageBox.information(self, "Success", message)
            self.accept()
        else:
            QMessageBox.critical(self, "Error", message)