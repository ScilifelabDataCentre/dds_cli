    


from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class FileManagerGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.layout.addWidget(QLabel("File Manager"))
        self.setLayout(self.layout)
