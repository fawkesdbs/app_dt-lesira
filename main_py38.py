import tkinter as tk
from dev_py38 import ui, config, state, logger, time_sync

# from dev_py38.ui import DowntimeTrackerUI
# from dev_py38.config import resource_path, log_dir
# from dev_py38.state import AppState
# from dev_py38.logger import DowntimeLogger
# from dev_py38.time_sync import TimeSync


def launch_app():
    """Launches the main application."""
    root = tk.Tk()
    time = time_sync.TimeSync()
    # log = logger.DowntimeLogger(config.log_dir)
    log = logger.DowntimeLogger(config.log_dir, time)
    sta = state.AppState(log)
    sta.load_active_downtimes_from_log()
    app = ui.DowntimeTrackerUI(root, sta)
    root.iconbitmap(config.resource_path("assets/icon.ico"))
    root.mainloop()


if __name__ == "__main__":
    launch_app()
