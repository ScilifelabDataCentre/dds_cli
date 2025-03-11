from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QDialog  
from PyQt6.QtGui import QPalette, QColor
from dds_cli.auth import Auth       


class AuthStatus(QWidget):
    def __init__(self, token_path: str):
        super().__init__()
        self.auth = Auth(authenticate=False, token_path=token_path)
        
        self.layout = QHBoxLayout()

        self.status_label = QLabel("Authentication Status: ")
        self.layout.addWidget(self.status_label)

        self.button = QPushButton("Check Status")    
        self.button.clicked.connect(self.get_status)
        self.layout.addWidget(self.button)
        
        self.setLayout(self.layout)
        
    def get_status(self):
        self.status = self.auth.check()
        if self.status:
            self.status_label.setText(f"Authentication Status: {self.status}")
        else:
            self.status_label.setText("Authentication Status: No token found")


class AuthLogout(QWidget):
    def __init__(self, token_path: str):
        super().__init__()
        self.auth = Auth(authenticate=False, token_path=token_path)
        
        self.layout = QHBoxLayout()
        self.layout.addWidget(QLabel("Logout"))
        self.button = QPushButton("Logout")
        self.button.clicked.connect(self.logout)
        self.layout.addWidget(self.button)
        self.setLayout(self.layout)
        
    def logout(self):

        dialog = QDialog()
        dialog.setWindowTitle("Logout")
        dialog.setModal(True)
        dialog.setLayout(QVBoxLayout())
        dialog.layout().addWidget(QLabel("Are you sure you want to logout?"))
        dialog.layout().addWidget(QPushButton("Logout"))
        dialog.exec()
        
        

class AuthLogin(QWidget):
    """
    This class is used to login to the DDS API.
    It is a QWidget that contains a QLineEdit for the username and password, and a QPushButton to login.
    """
    def __init__(self, auth: Auth, token_path: str):
        super().__init__()
        self.auth = auth
        self.token_path = token_path

        self.partial_token = None;
        #self.partial_token = None
        #self.secondfactor_method = None

        self.layout = QVBoxLayout() 
        self.layout.addWidget(QLabel("Login"))


        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        self.layout.addWidget(self.username)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.layout.addWidget(self.password)

       

        self.button = QPushButton("Login")
        self.button.clicked.connect(self.login)
        self.layout.addWidget(self.button)

        self.twofactor_code = QLineEdit()
        self.twofactor_code.setPlaceholderText("2FA Code")
        self.layout.addWidget(self.twofactor_code)

        self.auth_button = QPushButton("Authenticate")
        self.auth_button.clicked.connect(self.authenticate_2factor)
        self.layout.addWidget(self.auth_button)
        
        self.setLayout(self.layout)

    def login(self):
        print(self.username.text())
        print(self.password.text())
        
        self.auth = Auth(authenticate=False, 
                            authenticate_gui=True, 
                            token_path=self.token_path,
                            username_gui=self.username.text(), 
                            password_gui=self.password.text())
        self.partial_token = self.auth.token
        
        print(self.partial_token)

    def authenticate_2factor(self):
        print("Authenticating...")
        print(self.partial_token)
        print(type(self.twofactor_code.text()))
        #response = self.auth.authenticate_gui2f(partial_auth_token=self.partial_token, 
        #                          one_time_code=self.twofactor_code.text())
        
        #print(response)
        


class AuthGUI(QWidget):
    def __init__(self, token_path: str):
        super().__init__()
        self.auth = Auth(authenticate=False, token_path=token_path)
        self.layout = QVBoxLayout()
        
        self.layout.addWidget(AuthLogin(self.auth, token_path))
        self.setLayout(self.layout)
