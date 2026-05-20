import os
import json
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QComboBox, QListView, QMenu, QSystemTrayIcon, QDialog, QApplication
)
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush
from PySide6.QtCore import Qt, QDateTime, QTimer, QModelIndex

from task_model import Task, TaskModel, TaskFilterProxyModel
from task_dialog import TaskDialog
from task_delegate import TaskDelegate

MAIN_WINDOW_STYLESHEET = """
QMainWindow {
    background-color: #1e1e2e;
}
QWidget {
    font-family: "Segoe UI", Arial, sans-serif;
    color: #cdd6f4;
}
QLabel {
    font-size: 13px;
}
#app_title {
    font-size: 18px;
    font-weight: bold;
    color: #b4befe;
}
#stats_label {
    font-size: 12px;
    color: #a6adc8;
}
QLineEdit {
    background-color: #313244;
    border: 1.5px solid #45475a;
    border-radius: 8px;
    padding: 8px 12px;
    color: #cdd6f4;
    font-size: 13px;
}
QLineEdit:focus {
    border: 1.5px solid #b4befe;
}
QComboBox {
    background-color: #313244;
    border: 1.5px solid #45475a;
    border-radius: 8px;
    padding: 8px 12px;
    color: #cdd6f4;
    font-size: 13px;
    min-width: 90px;
}
QComboBox:focus {
    border: 1.5px solid #b4befe;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left-width: 0px;
}
QPushButton {
    background-color: #b4befe;
    color: #11111b;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: bold;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #cba6f7;
}
QPushButton:pressed {
    background-color: #89b4fa;
}
QPushButton#add_task_btn {
    background-color: #a6e3a1;
    color: #11111b;
}
QPushButton#add_task_btn:hover {
    background-color: #94e2d5;
}
QPushButton#dialog_cancel_btn {
    background-color: #313244;
    color: #cdd6f4;
    border: 1.5px solid #45475a;
}
QPushButton#dialog_cancel_btn:hover {
    background-color: #45475a;
}
QPushButton#dialog_save_btn {
    background-color: #a6e3a1;
    color: #11111b;
}
QPushButton#dialog_save_btn:hover {
    background-color: #94e2d5;
}
QListView {
    background-color: #181825;
    border: 2px solid #313244;
    border-radius: 10px;
    outline: none;
    padding: 6px;
}
QScrollBar:vertical {
    border: none;
    background: #181825;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #45475a;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #585b70;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}
"""


def create_app_icon():
    # Dynamically draw a checkmark icon to avoid missing resource issues
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Draw rounded background
    painter.setBrush(QBrush(QColor("#b4befe")))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(0, 0, 32, 32, 8, 8)

    # Draw checkmark inside
    painter.setPen(QPen(QColor("#11111b"), 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.drawLine(8, 16, 14, 22)
    painter.drawLine(14, 22, 24, 10)

    painter.end()
    return QIcon(pixmap)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Task Flow Manager")
        self.resize(550, 680)
        self.setWindowIcon(create_app_icon())
        self.setStyleSheet(MAIN_WINDOW_STYLESHEET)

        # Initialize Models & Delegate
        self.model = TaskModel()
        self.proxy_model = TaskFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)

        # Default Sort Configuration
        self.proxy_model.setSortRole(TaskModel.DueDateRole)
        self.proxy_model.sort(0, Qt.AscendingOrder)

        self.delegate = TaskDelegate()

        self.notified_task_ids = set()

        self.build_ui()
        self.setup_tray()

        # Connect signals for auto-saving
        self.model.dataChanged.connect(self.save_tasks)
        self.model.rowsInserted.connect(self.save_tasks)
        self.model.rowsRemoved.connect(self.save_tasks)

        # Connect stats updates
        self.model.dataChanged.connect(self.update_stats)
        self.model.rowsInserted.connect(self.update_stats)
        self.model.rowsRemoved.connect(self.update_stats)

        # Load initial tasks from storage
        self.load_tasks()
        self.update_stats()

        # System Timer for checking deadlines every 60 seconds
        self.alert_timer = QTimer(self)
        self.alert_timer.timeout.connect(self.check_deadlines)
        self.alert_timer.start(60000)  # 1 minute

    def build_ui(self):
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Title bar & stats
        title_layout = QHBoxLayout()
        title_label = QLabel("Task Flow")
        title_label.setObjectName("app_title")
        self.stats_label = QLabel("Pending: 0  |  Completed: 0")
        self.stats_label.setObjectName("stats_label")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.stats_label)
        layout.addLayout(title_layout)

        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search tasks...")
        self.search_input.textChanged.connect(self.on_search_changed)
        layout.addWidget(self.search_input)

        # Filter & Sort controls
        control_layout = QHBoxLayout()
        
        control_layout.addWidget(QLabel("Filter:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Pending", "Completed"])
        self.filter_combo.currentIndexChanged.connect(self.on_filter_changed)
        control_layout.addWidget(self.filter_combo)

        control_layout.addWidget(QLabel("Sort:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Due Date", "Priority", "Title"])
        self.sort_combo.currentIndexChanged.connect(self.on_sort_changed)
        control_layout.addWidget(self.sort_combo)

        control_layout.addStretch()

        self.add_btn = QPushButton("+ Add Task")
        self.add_btn.setObjectName("add_task_btn")
        self.add_btn.clicked.connect(self.add_task)
        control_layout.addWidget(self.add_btn)

        layout.addLayout(control_layout)

        # ListView
        self.list_view = QListView()
        self.list_view.setModel(self.proxy_model)
        self.list_view.setItemDelegate(self.delegate)
        self.list_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self.show_context_menu)
        self.list_view.doubleClicked.connect(self.edit_task)
        layout.addWidget(self.list_view)

        self.setCentralWidget(central_widget)

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(create_app_icon())

        tray_menu = QMenu(self)
        tray_menu.setStyleSheet("""
            QMenu {
                background-color: #242538;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
                color: #cdd6f4;
            }
            QMenu::item:selected {
                background-color: #b4befe;
                color: #11111b;
            }
        """)

        show_action = tray_menu.addAction("Show Window")
        show_action.triggered.connect(self.showNormal)
        show_action.triggered.connect(self.activateWindow)

        exit_action = tray_menu.addAction("Exit")
        exit_action.triggered.connect(QApplication.quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.on_tray_activated)

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()
                self.activateWindow()

    # Model operations
    def get_json_path(self):
        dir_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(dir_path, "tasks.json")

    def load_tasks(self):
        path = self.get_json_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                tasks = [Task.from_dict(d) for d in data]

                self.model.blockSignals(True)
                for task in tasks:
                    self.model.addTask(task)
                self.model.blockSignals(False)
        except Exception as e:
            print(f"Error loading tasks: {e}")

    def save_tasks(self):
        path = self.get_json_path()
        try:
            data = [task.to_dict() for task in self.model.tasks]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving tasks: {e}")

    def update_stats(self):
        total = len(self.model.tasks)
        completed = sum(1 for t in self.model.tasks if t.is_completed)
        pending = total - completed
        self.stats_label.setText(f"Pending: {pending}  |  Completed: {completed}  |  Total: {total}")

    # Control slots
    def on_search_changed(self, text):
        self.proxy_model.setSearchText(text)

    def on_filter_changed(self, index):
        filter_state = self.filter_combo.currentText()
        self.proxy_model.setFilterState(filter_state)

    def on_sort_changed(self, index):
        sort_text = self.sort_combo.currentText()
        if sort_text == "Due Date":
            self.proxy_model.setSortRole(TaskModel.DueDateRole)
            self.proxy_model.sort(0, Qt.AscendingOrder)
        elif sort_text == "Priority":
            self.proxy_model.setSortRole(TaskModel.PriorityRole)
            # High (3) sorted Descending so it shows first
            self.proxy_model.sort(0, Qt.DescendingOrder)
        elif sort_text == "Title":
            self.proxy_model.setSortRole(TaskModel.TitleRole)
            self.proxy_model.sort(0, Qt.AscendingOrder)

    def add_task(self):
        dialog = TaskDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            new_task = Task(
                title=data["title"],
                priority=data["priority"],
                due_date=data["due_date"]
            )
            self.model.addTask(new_task)
            self.update_stats()

    def edit_task(self):
        selected_indexes = self.list_view.selectedIndexes()
        if not selected_indexes:
            return
        
        proxy_index = selected_indexes[0]
        source_index = self.proxy_model.mapToSource(proxy_index)
        row = source_index.row()
        task = self.model.tasks[row]

        dialog = TaskDialog(self, title="Edit Task", priority=task.priority, due_date=task.due_date)
        dialog.title_input.setText(task.title)

        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            self.model.setData(source_index, data["title"], TaskModel.TitleRole)
            self.model.setData(source_index, data["priority"], TaskModel.PriorityRole)
            self.model.setData(source_index, data["due_date"], TaskModel.DueDateRole)
            self.update_stats()

    def delete_task(self):
        selected_indexes = self.list_view.selectedIndexes()
        if not selected_indexes:
            return

        proxy_index = selected_indexes[0]
        source_index = self.proxy_model.mapToSource(proxy_index)
        row = source_index.row()

        self.model.removeTask(row)
        self.update_stats()

    def show_context_menu(self, pos):
        index = self.list_view.indexAt(pos)
        if not index.isValid():
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #242538;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
                color: #cdd6f4;
            }
            QMenu::item:selected {
                background-color: #b4befe;
                color: #11111b;
            }
        """)

        is_completed = index.data(TaskModel.CompletedRole)
        toggle_text = "Mark Pending" if is_completed else "Mark Completed"

        toggle_action = menu.addAction(toggle_text)
        edit_action = menu.addAction("Edit Task")
        delete_action = menu.addAction("Delete Task")

        action = menu.exec(self.list_view.viewport().mapToGlobal(pos))
        source_index = self.proxy_model.mapToSource(index)

        if action == toggle_action:
            self.model.setData(source_index, not is_completed, TaskModel.CompletedRole)
            self.update_stats()
        elif action == edit_action:
            self.edit_task()
        elif action == delete_action:
            self.delete_task()

    def check_deadlines(self):
        now = QDateTime.currentDateTime()
        for task in self.model.tasks:
            if not task.is_completed and task.id not in self.notified_task_ids:
                secs = now.secsTo(task.due_date)
                # Alert if due in <= 15 minutes (900 seconds) and not overdue
                if 0 <= secs <= 900:
                    self.notified_task_ids.add(task.id)
                    mins = max(1, int(secs // 60))
                    self.tray_icon.showMessage(
                        "Task Deadline Approaching!",
                        f"Task '{task.title}' is due in {mins} minutes! ({task.priority} Priority)",
                        QSystemTrayIcon.Information,
                        5000
                    )

    def closeEvent(self, event):
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()

