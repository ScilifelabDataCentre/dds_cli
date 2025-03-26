pip install pyinstaller
pip install -r ../requirements.txt
pip install -r ../requirements-dev.txt
pyinstaller --onefile --name dds_gui_standalone --hidden-import textual.widgets._tab_pane --hidden-import cgi gui_standalone.py