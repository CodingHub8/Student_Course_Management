import sys
import os
from PySide6.QtGui import QIcon

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def get_app_icon():
    ico_path = get_resource_path("Logo Politeknik Malaysia.ico")
    if os.path.exists(ico_path):
        return QIcon(ico_path)
    png_path = get_resource_path("Logo Politeknik Malaysia.png")
    if os.path.exists(png_path):
        return QIcon(png_path)
    und_ico = get_resource_path("Logo_Politeknik_Malaysia.ico")
    if os.path.exists(und_ico):
        return QIcon(und_ico)
    return QIcon()
