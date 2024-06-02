import sys
import fitz  # Ensure PyMuPDF is installed
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QFileDialog, QListWidget, QListWidgetItem,
    QVBoxLayout, QHBoxLayout, QWidget, QLabel, QScrollArea, QMenu, QPushButton,
    QLineEdit, QMessageBox, QAbstractItemView, QTextBrowser
)
from PyQt5.QtGui import QIcon, QPixmap, QImage
from PyQt5.QtCore import Qt, QSize, QEvent, QItemSelectionModel

def handle_errors(func):
    """Decorator to handle and display errors."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            QMessageBox.critical(args[0], "Error", str(e))
    return wrapper

class PDFEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Mexie's Simple PDF")
        self.setGeometry(100, 100, 1200, 800)
        self.pdf_document = None
        self.current_file = None
        self.current_page = 0
        self.zoom_factor = 1.0
        self.history = []
        self.setupMenu()
        self.setupUIComponents()
        self.show()

    def setupMenu(self):
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('File')
        self.addMenuAction(fileMenu, 'Open', 'Ctrl+O', lambda: self.openFileDialog())
        self.addMenuAction(fileMenu, 'Save', 'Ctrl+S', lambda: self.saveFileDialog())
        self.addMenuAction(fileMenu, 'Save As', 'Ctrl+Shift+S', lambda: self.saveAsFileDialog())

        editMenu = menubar.addMenu('Edit')
        self.addMenuAction(editMenu, 'Merge', 'Ctrl+M', lambda: self.mergeFileDialog())
        self.addMenuAction(editMenu, 'Undo', 'Ctrl+Z', lambda: self.undo())

        aboutAction = QAction('About', self)
        aboutAction.triggered.connect(self.showAboutDialog)
        menubar.addAction(aboutAction)

    def addMenuAction(self, menu, name, shortcut, func):
        action = QAction(name, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(func)
        menu.addAction(action)

    def setupUIComponents(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        self.setupTopLayout(layout)
        self.setupMainLayout(layout)

    def setupTopLayout(self, parent_layout):
        top_layout = QHBoxLayout()
        top_layout.addStretch()
        self.addButton(top_layout, '-', self.zoomOut, 30)
        self.addButton(top_layout, '+', self.zoomIn, 30)
        self.zoom_value = self.addLineEdit(top_layout, "100%", 70, self.customZoom)
        self.page_indicator = self.addLabel(top_layout, "Page 0/0")
        top_layout.addStretch()
        parent_layout.addLayout(top_layout)

    def setupMainLayout(self, parent_layout):
        main_layout = QHBoxLayout()
        self.sidebar = self.addListWidget(main_layout, self.showContextMenu, self.sidebarItemClicked)
        self.scroll_area, self.page_label = self.addScrollArea(main_layout)
        self.addNavigationButtons(main_layout)
        parent_layout.addLayout(main_layout)

    def addButton(self, layout, text, func, width=None):
        button = QPushButton(text)
        if width:
            button.setFixedWidth(width)
        button.clicked.connect(func)
        layout.addWidget(button)
        return button

    def addLineEdit(self, layout, text, width, func):
        line_edit = QLineEdit()
        line_edit.setFixedWidth(width)
        line_edit.setText(text)
        line_edit.setAlignment(Qt.AlignCenter)
        line_edit.editingFinished.connect(func)
        layout.addWidget(line_edit)
        return line_edit

    def addLabel(self, layout, text):
        label = QLabel(text)
        layout.addWidget(label)
        return label

    def addListWidget(self, layout, context_menu_func, item_click_func):
        list_widget = QListWidget(self)
        list_widget.setFixedWidth(150)
        list_widget.setViewMode(QListWidget.IconMode)
        list_widget.setIconSize(QSize(100, 150))
        list_widget.setResizeMode(QListWidget.Adjust)
        list_widget.setMovement(QListWidget.Snap)
        list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        list_widget.customContextMenuRequested.connect(context_menu_func)
        list_widget.itemClicked.connect(item_click_func)
        list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        list_widget.setAcceptDrops(True)
        list_widget.setDragEnabled(False)
        list_widget.setDropIndicatorShown(True)
        layout.addWidget(list_widget)
        return list_widget

    def addScrollArea(self, layout):
        scroll_area = QScrollArea(self)
        page_label = QLabel(self)
        scroll_area.setWidget(page_label)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        return scroll_area, page_label

    def addNavigationButtons(self, layout):
        nav_layout = QVBoxLayout()
        self.addButton(nav_layout, '↑', self.previousPage, 30)
        self.addButton(nav_layout, '↓', self.nextPage, 30)
        layout.addLayout(nav_layout)

    @handle_errors
    def openFileDialog(self):
        fileName, _ = QFileDialog.getOpenFileName(self, 'Open PDF File', '', 'PDF Files (*.pdf)')
        if fileName:
            self.loadPDF(fileName)

    @handle_errors
    def saveFileDialog(self):
        if self.pdf_document:
            self.pdf_document.save(self.current_file)
            QMessageBox.information(self, "Save", "File saved successfully.")
        else:
            self.saveAsFileDialog()

    @handle_errors
    def saveAsFileDialog(self):
        fileName, _ = QFileDialog.getSaveFileName(self, 'Save PDF File As', '', 'PDF Files (*.pdf)')
        if fileName:
            self.current_file = fileName
            self.saveFileDialog()

    @handle_errors
    def mergeFileDialog(self):
        fileName, _ = QFileDialog.getOpenFileName(self, 'Merge PDF File', '', 'PDF Files (*.pdf)')
        if fileName:
            self.mergePDF(fileName)

    @handle_errors
    def loadPDF(self, file_path):
        self.pdf_document = fitz.open(file_path)
        self.current_file = file_path
        self.history.clear()
        self.updateSidebar()
        self.displayPage(0)
        self.updatePageIndicator()

    @handle_errors
    def savePDF(self, file_path):
        if self.pdf_document:
            self.pdf_document.save(file_path)
            QMessageBox.information(self, "Save", "File saved successfully.")

    @handle_errors
    def mergePDF(self, file_path):
        if self.pdf_document:
            merge_document = fitz.open(file_path)
            self.pdf_document.insert_pdf(merge_document)
            self.addToHistory()
            self.updateSidebar()
            self.displayPage(len(self.pdf_document) - merge_document.page_count)
            self.updatePageIndicator()

    def displayPage(self, page_number):
        page = self.pdf_document.load_page(page_number)
        pix = page.get_pixmap(matrix=fitz.Matrix(self.zoom_factor, self.zoom_factor))
        image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(image)
        self.page_label.setPixmap(pixmap)
        self.page_label.setAlignment(Qt.AlignCenter)
        self.current_page = page_number
        self.updatePageIndicator()

    def updateSidebar(self):
        self.sidebar.clear()
        for i in range(len(self.pdf_document)):
            page = self.pdf_document.load_page(i)
            pix = page.get_pixmap(matrix=fitz.Matrix(0.3, 0.3))
            image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            icon = QIcon(QPixmap.fromImage(image))
            item = QListWidgetItem(icon, f"Page {i + 1}")
            item.setData(Qt.UserRole, i)
            self.sidebar.addItem(item)

    def sidebarItemClicked(self, item):
        page_number = item.data(Qt.UserRole)
        self.displayPage(page_number)

    def showContextMenu(self, position):
        menu = QMenu()
        self.addContextMenuAction(menu, 'Delete Page', lambda: self.deleteSelectedPages())
        self.addContextMenuAction(menu, 'Move Up', lambda: self.moveSelectedPages('up'))
        self.addContextMenuAction(menu, 'Move Down', lambda: self.moveSelectedPages('down'))
        self.addContextMenuAction(menu, 'Rotate Page 90°', lambda: self.rotateSelectedPages())
        menu.exec_(self.sidebar.mapToGlobal(position))

    def addContextMenuAction(self, menu, name, func):
        action = QAction(name, self)
        action.triggered.connect(func)
        menu.addAction(action)

    @handle_errors
    def deleteSelectedPages(self):
        selected_items = self.sidebar.selectedItems()
        if selected_items:
            self.addToHistory()
            pages_to_delete = sorted([item.data(Qt.UserRole) for item in selected_items], reverse=True)
            for page_number in pages_to_delete:
                self.pdf_document.delete_page(page_number)
            self.updateSidebar()
            self.displayPage(min(max(0, self.current_page), len(self.pdf_document) - 1))
            self.updatePageIndicator()

    @handle_errors
    def moveSelectedPages(self, direction):
        selected_items = self.sidebar.selectedItems()
        if not selected_items:
            return
        row_indexes = sorted(self.sidebar.row(item) for item in selected_items)
        if direction == 'up' and row_indexes[0] == 0:
            return
        if direction == 'down' and row_indexes[-1] == self.sidebar.count() - 1:
            return
        if direction == 'up':
            for row in row_indexes:
                item = self.sidebar.takeItem(row)
                new_row = row - 1
                self.sidebar.insertItem(new_row, item)
                self.sidebar.setCurrentItem(item, QItemSelectionModel.Select)
        elif direction == 'down':
            for row in reversed(row_indexes):
                item = self.sidebar.takeItem(row)
                new_row = row + 1
                self.sidebar.insertItem(new_row, item)
                self.sidebar.setCurrentItem(item, QItemSelectionModel.Select)
        self.reorderPages()

    @handle_errors
    def reorderPages(self):
        new_document = fitz.open()
        for i in range(self.sidebar.count()):
            item = self.sidebar.item(i)
            page_number = item.data(Qt.UserRole)
            new_document.insert_pdf(self.pdf_document, from_page=page_number, to_page=page_number)
        self.pdf_document.close()
        self.pdf_document = new_document
        self.addToHistory()
        self.updateSidebar()
        self.displayPage(0)
        self.updatePageIndicator()

    @handle_errors
    def rotateSelectedPages(self):
        selected_items = self.sidebar.selectedItems()
        if selected_items:
            self.addToHistory()
            for item in selected_items:
                page_number = item.data(Qt.UserRole)
                page = self.pdf_document.load_page(page_number)
                page.set_rotation((page.rotation + 90) % 360)
            self.displayPage(self.current_page)
            self.updateSidebar()

    def eventFilter(self, source, event):
        if event.type() == QEvent.DragEnter:
            if event.mimeData().hasUrls():
                event.acceptProposedAction()
        elif event.type() == QEvent.Drop:
            if event.mimeData().hasUrls():
                for url in event.mimeData().urls():
                    self.mergePDF(url.toLocalFile())
                event.acceptProposedAction()
            elif source is self.sidebar:
                self.reorderPages()
        return super().eventFilter(source, event)

    def wheelEvent(self, event):
        num_degrees = event.angleDelta().y() / 8
        num_steps = num_degrees / 15
        if num_steps > 0:
            self.previousPage()
        else:
            self.nextPage()

    def previousPage(self):
        if self.current_page > 0:
            self.displayPage(self.current_page - 1)

    def nextPage(self):
        if self.current_page < len(self.pdf_document) - 1:
            self.displayPage(self.current_page + 1)

    def zoomIn(self):
        self.zoom_factor += 0.1
        self.displayPage(self.current_page)
        self.zoom_value.setText(f"{int(self.zoom_factor * 100)}%")

    def zoomOut(self):
        self.zoom_factor = max(0.1, self.zoom_factor - 0.1)
        self.displayPage(self.current_page)
        self.zoom_value.setText(f"{int(self.zoom_factor * 100)}%")

    def customZoom(self):
        try:
            zoom = float(self.zoom_value.text().replace('%', '')) / 100
            if zoom > 0:
                self.zoom_factor = zoom
                self.displayPage(self.current_page)
        except ValueError:
            pass

    def updatePageIndicator(self):
        if self.pdf_document:
            total_pages = len(self.pdf_document)
            self.page_indicator.setText(f"Page {self.current_page + 1}/{total_pages}")

    def addToHistory(self):
        if self.pdf_document:
            self.history.append(self.pdf_document.write())

    @handle_errors
    def undo(self):
        if self.history:
            previous_state = self.history.pop()
            self.pdf_document = fitz.open("pdf", previous_state)
            self.updateSidebar()
            self.displayPage(0)
            self.updatePageIndicator()

    def showAboutDialog(self):
        about_text = """<p>Version 1</p>
                        <p>Created with ChatGPT</p>
                        <p>Follow me at <a href='https://x.com/Mexie__'>x.com/Mexie__</a> for randomness</p>"""
        QMessageBox.about(self, "About Mexie's Simple PDF", about_text)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    editor = PDFEditor()
    sys.exit(app.exec_())
