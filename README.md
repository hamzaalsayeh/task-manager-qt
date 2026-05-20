# Task Flow Manager

A premium desktop Task Manager application built with Python 3 and PySide6 (Qt Widgets). It features a modern dark-themed user interface, custom list card styling, real-time search/sorting/filtering, background deadline monitoring, and system tray integration.

## Features
- **Modern Dark UI**: Beautifully styled using custom Qt Style Sheets (QSS) with smooth hover states.
- **Model-View Architecture**: Uses `QAbstractListModel` and `QSortFilterProxyModel` for clean data separation and instant search/sort.
- **Custom Card Delegates**: Renders task items as cards with color-coded priority badges (High/Medium/Low), relative deadline warnings, custom interactive checkboxes, and automatic text strike-throughs on completion.
- **JSON Storage**: Tasks automatically load and auto-save on every modification to `tasks.json`.
- **System Tray & Alerts**: Minimize/close actions hide the app to the system tray (`QSystemTrayIcon`), while a background timer checks deadlines and triggers native desktop alerts 15 minutes before tasks are due.

## File Structure
- `main.py`: Entry point and main Qt event loop.
- `main_window.py`: Controls layouts, tray icon, timers, and context menus.
- `task_model.py`: Custom task model and sorting proxy configuration.
- `task_dialog.py`: Task input form with text validation.
- `task_delegate.py`: Custom painting class for item cards.
- `run_task_manager.bat`: Double-click script launcher for Windows.

## Installation & Running
1. Install PySide6: `pip install PySide6`
2. Run the application: `python main.py` or double-click `run_task_manager.bat`.
