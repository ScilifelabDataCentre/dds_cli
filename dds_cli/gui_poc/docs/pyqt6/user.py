from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem
from dds_cli.account_manager import AccountManager

class ListUserInfo(QTableWidget):
    def __init__(self, user_info: dict):
        super().__init__()  
        self.user_info = user_info
        
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(["Key", "Value"])
        
        self.setRowCount(len(self.user_info))
        for i, (key, value) in enumerate(self.user_info.items()):
            self.setItem(i, 0, QTableWidgetItem(key))
            self.setItem(i, 1, QTableWidgetItem(str(value)))

class ListUsers(QTableWidget):
    def __init__(self, users: list, keys: list):
        super().__init__()
        self.users = users
        self.keys = keys
        
        self.setColumnCount(len(self.keys))
        self.setHorizontalHeaderLabels(self.keys)
        
        self.setRowCount(len(self.users))
        for i, user in enumerate(self.users):
            for j, key in enumerate(self.keys):
                self.setItem(i, j, QTableWidgetItem(str(user[key])))
        

class AccountManagerGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.account_manager = AccountManager()

        self.layout = QVBoxLayout()
        self.layout.addWidget(QLabel("User Info"))
        self.layout.addWidget(ListUserInfo(self.get_user_info()))
        
        self.layout.addWidget(QLabel("Users"))
        self.layout.addWidget(ListUsers(self.get_users()[0], self.get_users()[1]))
        
        self.setLayout(self.layout)

        self.get_users()
        
    def get_user_info(self) -> dict:
        return self.account_manager.get_user_info() 
    
    def get_users(self) -> tuple:
        return self.account_manager.list_users()
