# -*- mode: python ; coding: utf-8 -*-

excludes = [
    'tkinter', '_tkinter', 'tcl', 'ttk',
    'matplotlib', 'scipy', 'notebook', 'jupyter', 'IPython', 'ipykernel',
    'unittest', 'doctest', 'test',
    'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
    'PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.Qt3DInput', 'PySide6.Qt3DAnimation', 'PySide6.Qt3DExtras',
    'PySide6.QtQuick', 'PySide6.QtQml', 'PySide6.QtDesigner', 'PySide6.QtHelp',
    'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
    'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets',
    'PySide6.QtPositioning', 'PySide6.QtSensors', 'PySide6.QtSql',
    'PySide6.QtSvg', 'PySide6.QtSvgWidgets', 'PySide6.QtTest', 'PySide6.QtXml',
    'PySide6.QtNetwork', 'PySide6.QtNfc', 'PySide6.QtPdf', 'PySide6.QtPdfWidgets',
    'PySide6.QtRemoteObjects', 'PySide6.QtScxml', 'PySide6.QtSerialPort',
    'PySide6.QtSpatialAudio', 'PySide6.QtVirtualKeyboard', 'PySide6.QtWebChannel', 'PySide6.QtWebSockets'
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('Logo Politeknik Malaysia.ico', '.'),
        ('Logo Politeknik Malaysia.png', '.'),
        ('config.ini', '.')
    ],
    hiddenimports=[
        'psycopg2',
        'psycopg2.pool',
        'psycopg2.extras',
        'bcrypt',
        'pdfplumber',
        'pandas'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Politeknik_Course_Management',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='Logo Politeknik Malaysia.ico',
)
