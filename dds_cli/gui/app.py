from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtWidgets import QApplication
import sys
from dds_cli.gui.user import AccountManagerGUI

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DDS GUI POC")
        self.setGeometry(800, 600)
        
        self.account_manager_gui = AccountManagerGUI()
        self.setCentralWidget(self.account_manager_gui)
        
        
class GUI:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.main_window = MainWindow()
        self.main_window.show()
    
    def exec(self):
        self.app.exec()
    
