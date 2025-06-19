from datetime import datetime
import os
import json
from typing import Optional
from .time_sync import TimeSync


class OperatorMovementLogger:
    """
    Logs operator sign-in and sign-out events to daily JSON log files.
    """

    def __init__(self, log_dir_path: str, time_sync: Optional[TimeSync] = None):
        self.log_dir_path = log_dir_path
        self.time_sync = time_sync

    def _get_today_str(self) -> str:
        now = self.time_sync.get_now() if self.time_sync else datetime.now()
        return now.strftime("%Y-%m-%d")

    def _get_log_file_path(self, date_str: Optional[str] = None) -> str:
        if date_str is None:
            date_str = self._get_today_str()
        return os.path.join(self.log_dir_path, f"operator_signinout_{date_str}.json")

    def _load_log(self, log_file: str):
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not isinstance(data, list):
                        data = []
            except Exception:
                data = []
        else:
            data = []
        return data

    def log_event(self, operator: str, station: str, state: str):
        """
        Log an operator sign-in or sign-out event to the daily log file.

        :param operator: Operator ID or name
        :param station: Station name
        :param state: "sign in" or "sign out"
        """
        now = self.time_sync.get_now() if self.time_sync else datetime.now()
        event = {
            "operator": operator,
            "station": station,
            "time": now.isoformat(timespec="seconds"),
            "state": state,
        }
        log_file = self._get_log_file_path()
        data = self._load_log(log_file)

        last_event = None
        for e in reversed(data):
            if e.get("operator") == operator:
                last_event = e
                break

        if last_event and last_event.get("state") == state:
            # Prevent duplicate consecutive sign in/out
            print(f"Operator '{operator}' already '{state}'. Event not logged.")
            return

        data.append(event)
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
