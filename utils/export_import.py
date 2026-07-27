import csv
import os
from database.connection import get_connection
from database.models import get_all_students, get_all_courses
from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrinter

def export_to_csv(file_path):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.MatricNo, s.Name, s.Class, s.CurrentCGPA, s.TotalCreditsEarned, s.CurrentSemesterCredits, s.Program, s.CurrentSemester
                FROM Students s ORDER BY s.MatricNo
            """)
            students = cur.fetchall()

    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["MatricNo", "Name", "Class", "CurrentCGPA", "TotalCreditsEarned", "CurrentSemesterCredits", "Program", "CurrentSemester"])
        for row in students:
            writer.writerow(row)
    return True

def export_to_xlsx(file_path):
    # Generates a standard XML spreadsheet format (SpreadsheetML) compatible with MS Excel without requiring external libs
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.MatricNo, s.Name, s.Class, s.CurrentCGPA, s.TotalCreditsEarned, s.CurrentSemesterCredits, s.Program, s.CurrentSemester
                FROM Students s ORDER BY s.MatricNo
            """)
            students = cur.fetchall()

    content = ['<?xml version="1.0"?>',
               '<?mso-application progid="Excel.Sheet"?>',
               '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"',
               ' xmlns:o="urn:schemas-microsoft-com:office:office"',
               ' xmlns:x="urn:schemas-microsoft-com:office:excel"',
               ' xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">',
               '<Worksheet ss:Name="Students"><Table>']
    
    headers = ["MatricNo", "Name", "Class", "CurrentCGPA", "TotalCreditsEarned", "CurrentSemesterCredits", "Program", "CurrentSemester"]
    content.append('<Row>' + ''.join(f'<Cell><Data ss:Type="String">{h}</Data></Cell>' for h in headers) + '</Row>')
    
    for row in students:
        cells = []
        for val in row:
            v_type = "Number" if isinstance(val, (int, float)) else "String"
            cells.append(f'<Cell><Data ss:Type="{v_type}">{val if val is not None else ""}</Data></Cell>')
        content.append('<Row>' + ''.join(cells) + '</Row>')
    
    content.append('</Table></Worksheet></Workbook>')
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(content))
    return True

def export_to_pdf(file_path):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.MatricNo, s.Name, s.Class, s.CurrentCGPA, s.TotalCreditsEarned, s.Program, s.CurrentSemester
                FROM Students s ORDER BY s.MatricNo
            """)
            students = cur.fetchall()

    html = """
    <html>
    <head>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h2 { color: #1e1e2e; text-align: center; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { border: 1px solid #45475a; padding: 8px; text-align: left; font-size: 11px; }
        th { background-color: #313244; color: #ffffff; }
        tr:nth-child(even) { background-color: #f2f2f2; }
    </style>
    </head>
    <body>
        <h2>🎓 Politeknik Student Academic Report</h2>
        <table>
            <tr>
                <th>Matric No</th>
                <th>Full Name</th>
                <th>Class</th>
                <th>CGPA</th>
                <th>Earned Credits</th>
                <th>Program</th>
                <th>Semester</th>
            </tr>
    """
    for r in students:
        html += f"""
            <tr>
                <td>{r[0]}</td>
                <td>{r[1]}</td>
                <td>{r[2] or ''}</td>
                <td>{r[3]:.2f}</td>
                <td>{r[4]:.1f}</td>
                <td>{r[5] or ''}</td>
                <td>{r[6]}</td>
            </tr>
        """
    html += "</table></body></html>"

    doc = QTextDocument()
    doc.setHtml(html)
    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(file_path)
    doc.print_(printer)
    return True

def export_to_docx(file_path):
    # Generates a Word Document XML format compatible with MS Word (.docx / .xml)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT s.MatricNo, s.Name, s.Class, s.CurrentCGPA, s.TotalCreditsEarned, s.Program
                FROM Students s ORDER BY s.MatricNo
            """)
            students = cur.fetchall()

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<?mso-application progid="Word.Document"?>
<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml">
  <w:body>
    <w:p><w:r><w:t>Politeknik Student Management Report</w:t></w:r></w:p>
    <w:tbl>
      <w:tr>
        <w:tc><w:p><w:r><w:t>Matric</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>Name</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>Class</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>CGPA</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>Credits</w:t></w:r></w:p></w:tc>
      </w:tr>""")
        for s in students:
            f.write(f"""
      <w:tr>
        <w:tc><w:p><w:r><w:t>{s[0]}</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>{s[1]}</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>{s[2] or ''}</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>{s[3]:.2f}</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>{s[4]:.1f}</w:t></w:r></w:p></w:tc>
      </w:tr>""")
        f.write("""
    </w:tbl>
  </w:body>
</w:wordDocument>""")
    return True
