from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys
import os
import subprocess
import webbrowser


class LineNumbers(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        self.editor.blockCountChanged.connect(self.update_line_numbers)
        self.editor.updateRequest.connect(self.update_line_area)
        self.font = QFont()
        self.font.setPointSize(10)
        self.update_line_numbers()

    def update_line_numbers(self):
        digits = len(str(self.editor.blockCount()))
        width = self.fontMetrics().width('9' * digits)
        self.setFixedWidth(width + 10)

    def update_line_area(self, rect, dy):
        if dy:
            self.scroll(0, dy)
        else:
            self.update(0, rect.y(), self.width(), rect.height())
        self.update_line_numbers()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(event.rect(), Qt.lightGray)

        block = self.editor.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.editor.blockBoundingGeometry(block).translated(self.editor.contentOffset()).top()
        bottom = top + self.editor.blockBoundingRect(block).height()

        height = self.editor.fontMetrics().height()
        while block.isValid():
            if block.isVisible() and (bottom >= event.rect().top()):
                number = str(blockNumber + 1)
                point = QPointF(0, top + 10)
                painter.setPen(Qt.black)
                painter.drawText(point, number)

            block = block.next()
            top = bottom
            bottom = top + self.editor.blockBoundingRect(block).height()
            blockNumber += 1

class CodeEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.modified = False
        self.current_file = None
                
        self.auto_save_timer = QTimer()
        self.auto_save_interval = 1000
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.init_ui()
        
        self.setWindowTitle("Coder")
        self.setWindowIcon(QIcon('icon.png'))
        self.setMinimumSize(QSize(400, 300))

        self.menu_bar = self.menuBar()
        
        edit_menu = self.menu_bar.addMenu('Edit')
        
        run_menu = self. menu_bar.addMenu('Run')
        setting_menu = self.menu_bar.addMenu('Setting')

        self.copyAction = edit_menu.addAction('Copy')
        self.copyAction.triggered.connect(self.copy_action)
        self.copyAction.setShortcut(QKeySequence.Copy)
        
        self.cutAction = edit_menu.addAction('Cut')
        self.cutAction.triggered.connect(self.cut_action)
        self.cutAction.setShortcut(QKeySequence.Cut)
        
        self.pasteAction = edit_menu.addAction('Paste')
        self.pasteAction.triggered.connect(self.paste_action)
        self.pasteAction.setShortcut(QKeySequence.Paste)
        
        self.findAction = edit_menu.addAction('Find')
        self.findAction.triggered.connect(self.find_action)
        self.findAction.setShortcut("Ctrl+F")

        self.run_debuggerAction = run_menu.addAction('Run debugger')
        self.run_debuggerAction.triggered.connect(self.run_debugger)
        self.run_debuggerAction.setShortcut("Ctrl+R")
        
        self.aboutAction = setting_menu.addAction('About')
        self.aboutAction.triggered.connect(self.about_action)
        self.aboutAction.setShortcut("Ctrl+A")

        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        self.add_new_tab()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.close_tab_shortcut = QShortcut(QKeySequence("Ctrl+W"), self)
        self.close_tab_shortcut.activated.connect(self.close_current_tab)

    def close_current_tab(self):
        current_tab_index = self.tab_widget.currentIndex()
        
        if current_tab_index >= 0:
            self.tab_widget.removeTab(current_tab_index)

    def init_ui(self):
        self.file_menu = self.menuBar().addMenu('File')
        
        self.newAction = self.file_menu.addAction('New file')
        self.newAction.triggered.connect(self.new_action)
        self.newAction.setShortcut("Ctrl+N")
        
        self.openAction = self.file_menu.addAction('Open')
        self.openAction.triggered.connect(self.open)
        self.openAction.setShortcut("Ctrl+O")
        
        self.saveAction = self.file_menu.addAction('Save')
        self.saveAction.triggered.connect(self.save)
        self.saveAction.setShortcut("Ctrl+S")
        
        self.saveAsAction = self.file_menu.addAction('Save as...')
        self.saveAsAction.triggered.connect(self.saveAs)
        self.saveAsAction.setShortcut("Ctrl+Q")
        
        self.auto_save_action = self.file_menu.addAction("Auto Save")
        self.auto_save_action.setCheckable(True)
        self.auto_save_action.triggered.connect(self.toggle_auto_save)
        self.auto_save_action.setShortcut("Ctrl+E")

    def toggle_auto_save(self, state):
        if state:
            if not self.current_file:
                print("Please save the file first before enabling auto-save.")
                self.auto_save_action.setChecked(False)
                return
            self.auto_save_timer.start(self.auto_save_interval)
        else:
            self.auto_save_timer.stop()

    def auto_save(self):
        if self.modified and self.current_file:
            text = self.text_area.toPlainText()
            try:
                with open(self.current_file, 'w') as file:
                    file.write(text)
                print(f"Auto-save: File {self.current_file} saved.")
                self.modified = False
            except Exception as e:
                print(f"Error auto-saving file: {e}")
    
    def add_new_tab(self):
        new_tab = QWidget()
        layout = QGridLayout(new_tab)

        self.file_system_model = QFileSystemModel()
        self.file_system_model.setRootPath(QDir.rootPath())

        self.text_area = QPlainTextEdit()
        self.line_numbers = LineNumbers(self.text_area)
        self.text_area.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.text_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.text_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.text_area.textChanged.connect(self.update_modified)

        self.file_system_model = QFileSystemModel()
        self.file_system_model.setRootPath(QDir.rootPath())

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.file_system_model)
        self.tree_view.setRootIndex(self.file_system_model.index(QDir.rootPath()))
        self.tree_view.setFixedWidth(200)
        self.tree_view.selectionModel().currentChanged.connect(self.file_selected)

        layout.addWidget(self.line_numbers, 0, 0)
        layout.addWidget(self.text_area, 0, 1)
        layout.addWidget(self.tree_view, 0, 2, 2, 1)

        new_tab.setLayout(layout)
        self.tab_widget.addTab(new_tab, 'New File')
            
            
    def update_modified(self):
        self.modified = True
            
    def open(self):
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, 'Open', "", "All Files (*)", options=options)
        if fileName:
            self.current_file = fileName
            with open(fileName, 'r') as file:
                content = file.read()
            self.text_area.setPlainText(content)
            print(f"File {fileName} opened.")
            self.tree_view.setRootIndex(self.file_system_model.index(os.path.dirname(fileName)))
            self.open_file_in_new_tab(fileName)

    def save(self):
        text_area = self.get_current_text_area()

        if text_area:
            if self.current_file is None:
                # Если файл новый, вызываем диалог «Сохранить как»
                self.save_as()
            else:
                # Сохраняем данные в уже открытый файл
                try:
                    with open(self.current_file, 'w', encoding='utf-8') as file:
                        file.write(text_area.toPlainText())
                    self.modified = False
                    print(f"File '{self.current_file}' saved successfully.")
                except Exception as e:
                    print(f"Error: Unable to save file: {e}")

    def save_as(self):
        text_area = self.get_current_text_area()

        if text_area:
            # Открываем диалог для выбора файла
            file_filter = "All Files (*);;Python (*.py);;C++ (*.cpp);;HTML (*.html);;CSS (*.css);;Text file (*.txt);;Windows batch (*.bat)"
            file_path, _ = QFileDialog.getSaveFileName(self, "Save File As", "", file_filter)

            if file_path:
                try:
                    with open(file_path, 'w', encoding='utf-8') as file:
                        file.write(text_area.toPlainText())
                    self.current_file = file_path  # Обновляем путь файла
                    self.modified = False
                    print(f"File saved successfully as '{file_path}'.")
                except Exception as e:
                    print(f"Error: Unable to save file as: {e}")

            
    def saveAs(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_filter = "All Files (*);;Python (*.py);;C++ (*.cpp);;HTML (*.html);;CSS (*.css);;Text file (*.txt);;Windows batch (*.bat)"
        fileName, selected_filter = QFileDialog.getSaveFileName(self, 'Save as...', "", file_filter, options=options)
        if fileName:
            self.current_file = fileName
            text = self.text_area.toPlainText()
            try:
                file_extension = ""
                if selected_filter.startswith("Python"):
                    file_extension = ".py"
                elif selected_filter.startswith("C++"):
                    file_extension = ".cpp"
                elif selected_filter.startswith("HTML"):
                    file_extension = ".html"
                elif selected_filter.startswith("CSS"):
                    file_extension = ".css"
                elif selected_filter.startswith("Text file"):
                    file_extension = ".txt"
                elif selected_filter.startswith("Windows batch"):
                    file_extension = ".bat"
                if file_extension and not fileName.endswith(file_extension):
                    fileName += file_extension
                with open(fileName, 'w', encoding='utf-8') as file:
                    file.write(text)
                print(f"File {fileName} saved.")
                self.tab_widget.setTabText(self.tab_widget.currentIndex(), os.path.basename(fileName))
                self.tree_view.setRootIndex(self.file_system_model.index(os.path.dirname(fileName)))
            except Exception as e:
                print(f"Error saving file: {e}")
            
    def update_line_numbers(self):
        self.line_numbers.update_line_numbers()

    def new_action(self):
        new_tab = QWidget()
        layout = QGridLayout(new_tab)
        text_area = QPlainTextEdit()
        text_area.setLineWrapMode(QPlainTextEdit.NoWrap)
        text_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        text_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        line_numbers = LineNumbers(text_area)
        file_system_model = QFileSystemModel()
        file_system_model.setRootPath(QDir.rootPath())
        tree_view = QTreeView()
        tree_view.setModel(file_system_model)
        tree_view.setRootIndex(file_system_model.index(QDir.rootPath()))
        tree_view.setFixedWidth(200)
        layout.addWidget(line_numbers, 0, 0)
        layout.addWidget(text_area, 0, 1)
        layout.addWidget(tree_view, 0, 2, 2, 1)
        new_tab.setLayout(layout)
        self.tab_widget.addTab(new_tab, 'New File')
        self.tab_widget.setCurrentWidget(new_tab)
        self.current_file = None
        self.modified = True

    def about_action(self):
        aboutWindow = About()
        aboutWindow.show()

    def find_action(self):
        findWindow = Find(self)
        findWindow.show()
    
    def close_tab(self, index):
        self.tab_widget.removeTab(index)
        if self.tab_widget.count() == 0:
            self.close()
    
    def get_current_text_area(self):
        current_tab_index = self.tab_widget.currentIndex()
        current_tab = self.tab_widget.widget(current_tab_index)
        return current_tab.findChild(QPlainTextEdit)

    def copy_action(self):
        text_area = self.get_current_text_area()
        if text_area:
            text_area.copy()

    def cut_action(self):
        text_area = self.get_current_text_area()
        if text_area:
            text_area.cut()

    def paste_action(self):
        text_area = self.get_current_text_area()
        if text_area:
            text_area.paste()
    
    def file_selected(self, index):
        file_path = self.file_system_model.filePath(index)
        if os.path.isfile(file_path):
            try:
                self.open_file_in_new_tab(file_path)  # Всегда открывать в новой вкладке
            except Exception as e:
                print(f"Error: Unable to open file: {e}")

            
    def open_file_in_new_tab(self, file_path=None):
        new_tab = QWidget()
        layout = QGridLayout(new_tab)

        text_area = QPlainTextEdit()
        line_numbers = LineNumbers(text_area)
        text_area.textChanged.connect(self.update_modified)
        text_area.setLineWrapMode(QPlainTextEdit.NoWrap)
        text_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        text_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                text_area.setPlainText(content)
            except FileNotFoundError:
                # Handling the FileNotFoundError
                print(f"Error: File '{file_path}' not found.")
                # Optional: You can show a message box to inform the user
                QMessageBox.critical(self, "Error", f"File '{file_path}' not found.")
                return
            except UnicodeDecodeError:
                QMessageBox.critical(self, "Error", f"Failed to open file: Encoding error.")
                return

            
        layout.addWidget(line_numbers, 0, 0)
        layout.addWidget(text_area, 0, 1)

        tree_view = QTreeView()
        tree_view.setModel(self.file_system_model)
        tree_view.setRootIndex(self.file_system_model.index(QDir.rootPath()))
        tree_view.setFixedWidth(200)
        tree_view.selectionModel().currentChanged.connect(self.file_selected)
        layout.addWidget(tree_view, 0, 2, 2, 1)

        new_tab.setLayout(layout)
        self.tab_widget.addTab(new_tab, os.path.basename(file_path) if file_path else 'New File')
        self.tab_widget.setCurrentWidget(new_tab)
    
    def run_debugger(self):
        self.save()
        current_tab_index = self.tab_widget.currentIndex()
        current_tab = self.tab_widget.widget(current_tab_index)
        text_area = current_tab.findChild(QPlainTextEdit)
        
        if text_area:
            code = text_area.toPlainText()
            tab_title = self.tab_widget.tabText(current_tab_index)
            
            if "." in tab_title:
                file_extension = tab_title.split('.')[-1]
            else:
                file_extension = None
            
            if file_extension == "py":
                command = f"sudo python3 {self.current_file}"
                try:
                    subprocess.run(f"xterm -hold -e '{command}'", shell=True)
                except Exception as e:
                    print(f"Error running Python code: {e}")
            
            elif file_extension == "cpp":
                # Убираем расширение .cpp из названия вкладки, чтобы получить имя исполняемого файла
                executable_name = tab_title.replace('.cpp', '')
                compile_command = f"g++ {self.current_file} -o {executable_name}"
                try:
                    subprocess.run(f"xterm -hold -e '{compile_command}'", shell=True)
                    run_command = f"sudo ./{executable_name}"
                    subprocess.run(f"xterm -hold -e '{run_command}'", shell=True)
                except Exception as e:
                    print(f"Error running C++ code: {e}")
            
            elif file_extension == "html":
                try:
                    with open("temp.html", 'w') as file:
                        file.write(code)
                    webbrowser.open("temp.html")
                except Exception as e:
                    print(f"Error opening HTML file in browser: {e}")
            
            else:
                print("The file cannot be run.")

class About(QWidget):
    closed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('About')
        self.setWindowIcon(QIcon('icon.png'))
        self.setFixedSize(QSize(250, 100))
        self.closeEvent = self.on_close
        
        self.label = QLabel('Coder\nVersion: 1.1.0\nAutor: OrgInfoTech', self)
        self.label.setGeometry(5, 0, 245, 100)
        self.label.setStyleSheet('font-size: 20px')

    def on_close(self, event):
        self.closed.emit()
        self.close()

class Find(QWidget):
    closed = pyqtSignal()

    def __init__(self, editor):
        super().__init__()
        self.editor = editor
        self.init_ui()
        self.current_search_position = 0
        self.text_area = None

    def init_ui(self):
        self.setWindowTitle('Find')
        self.setWindowIcon(QIcon('icon.png'))
        self.setFixedSize(QSize(200, 70))
        self.closeEvent = self.on_close
        
        self.input = QLineEdit(self)
        self.input.setGeometry(5, 5, 190, 30)
        
        self.findButton = QPushButton('Find', self)
        self.findButton.setGeometry(145, 35, 50, 30)
        self.findButton.clicked.connect(self.find)

    def on_close(self, event):
        self.closed.emit()
        self.close()
        
    def find(self):
        current_tab_index = self.editor.tab_widget.currentIndex()
        current_tab = self.editor.tab_widget.widget(current_tab_index)
        self.text_area = current_tab.findChild(QPlainTextEdit)
        
        if self.text_area is not None:
            full_text = self.text_area.toPlainText()
            search_text = self.input.text()

            index = full_text.find(search_text, self.current_search_position)

            if index != -1:
                cursor = self.text_area.textCursor()
                cursor.setPosition(index)
                cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, len(search_text))

                self.text_area.setTextCursor(cursor)

                self.current_search_position = index + len(search_text)

                self.text_area.setFocus()

            else:
                self.current_search_position = 0
                print(f"String '{search_text}' not found.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = CodeEditor()
    
    # Check if a file path is provided as a command-line argument
    if len(sys.argv) > 1:
        # The file path is provided as the first command-line argument
        file_path = sys.argv[1]
        editor.open_file_in_new_tab(file_path)
    
    editor.show()
    sys.exit(app.exec_())