import tkinter as tk
from core import app_state, config, downtime_logger, time_sync, operator_movement_logger
from ui import ui


def launch_app():
    """Launches the main application."""
    root = tk.Tk()
    # root.update()
    # root.deiconify()
    time = time_sync.TimeSync()
    # log = downtime_logger.DowntimeLogger(config.log_dir)
    log = downtime_logger.DowntimeLogger(config.db_config, time)
    mov = operator_movement_logger.OperatorMovementLogger(config.db_config, time)
    sta = app_state.AppState(log)
    sta.load_active_downtimes_from_log()
    app = ui.DowntimeTrackerUI(root, sta, mov, time)
    # app = ui.DowntimeTrackerUI(root, sta)
    root.iconbitmap(config.resource_path("assets/icon.ico"))
    root.mainloop()


if __name__ == "__main__":
    launch_app()
