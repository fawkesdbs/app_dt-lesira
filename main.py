import tkinter as tk
from core import config, logger, state, time_sync
from ui import ui


def launch_app():
    """Launches the main application."""
    root = tk.Tk()
    time = time_sync.TimeSync()
    # log = logger.DowntimeLogger(config.log_dir)
    log = logger.DowntimeLogger(config.log_dir, time)
    sta = state.AppState(log)
    sta.load_active_downtimes_from_log()
    app = ui.DowntimeTrackerUI(root, sta, time)
    root.iconbitmap(config.resource_path("assets/icon.ico"))
    root.mainloop()


if __name__ == "__main__":
    launch_app()
