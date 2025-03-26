pip install pyinstaller
pyinstaller --onefile --name dds_gui_standalone --hidden-import textual.widgets._tab_pane gui_standalone.py