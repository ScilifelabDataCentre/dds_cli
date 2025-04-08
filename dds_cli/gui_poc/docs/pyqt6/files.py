    


from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt6.QtWidgets import QFileDialog

class FileManagerGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.layout.addWidget(QLabel("File Manager"))
        self.setLayout(self.layout)

        self.file_path = QLabel("No file selected")
        self.layout.addWidget(self.file_path)

        self.button = QPushButton("Select File")
        self.button.clicked.connect(self.select_file)
        self.layout.addWidget(self.button)

    def select_file(self):
        file_dialoge = QFileDialog()
        file_dialoge.setFileMode(QFileDialog.FileMode.AnyFile)
        file_dialoge.exec()
        print(file_dialoge.selectedFiles())
        self.file_path.setText(file_dialoge.selectedFiles()[0])