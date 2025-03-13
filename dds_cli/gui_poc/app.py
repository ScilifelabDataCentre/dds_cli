from PyQt6.QtWidgets import QMainWindow, QTabWidget
from PyQt6.QtWidgets import QApplication
import sys
from dds_cli.gui_poc.auth import AuthStatus, AuthLogout
from dds_cli.gui_poc.user import AccountManagerGUI
from dds_cli.gui_poc.files import FileManagerGUI

class MainWindow(QMainWindow):
    def __init__(self, token_path: str):
        super().__init__()
        self.setWindowTitle("DDS GUI POC")
        #self.setGeometry(100, 100, 800, 600)

        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.TabPosition.North)
        tabs.setDocumentMode(True)

        tabs.addTab(AuthStatus(token_path), "Auth Status")
        tabs.addTab(AuthLogout(token_path), "Auth Logout")
        tabs.addTab(FileManagerGUI(), "File Manager")

        self.setCentralWidget(tabs)
        
        #self.account_manager_gui = AccountManagerGUI()
        #self.setCentralWidget(self.account_manager_gui)
        
        
class GUI:
    def __init__(self, token_path: str):
        self.app = QApplication(sys.argv)
        self.main_window = MainWindow(token_path)
        self.main_window.show()
    
    def exec(self):
        self.app.exec()
    
