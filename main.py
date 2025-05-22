import tkinter as tk
from ui import DowntimeTrackerUI
from config import resource_path, log_dir
from state import AppState
from logger import DowntimeLogger


def launch_app():
    """Launches the main application."""
    root = tk.Tk()
    logger = DowntimeLogger(log_dir)
    state = AppState(logger)
    state.load_active_downtimes_from_log()
    app = DowntimeTrackerUI(root, state)
    root.iconbitmap(resource_path("assets/icon.ico"))
    root.mainloop()


if __name__ == "__main__":
    launch_app()
