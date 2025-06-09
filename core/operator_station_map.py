import os
import json
from datetime import datetime, date
from typing import Dict, Optional
from .time_sync import TimeSync


class OperatorStationMap:
    def __init__(
        self,
        log_dir_path: str,
        filename: str = "operator_station_map.json",
        time_sync: Optional[TimeSync] = None,
    ):
        self.file_path = os.path.join(log_dir_path, filename)
        self.last_cleared_file = os.path.join(
            log_dir_path, "operator_station_map_last_cleared.txt"
        )
        self._map: Dict[str, str] = {}
        self.time_sync = time_sync
        self._load()

    def _get_today(self) -> date:
        return self.time_sync.get_now().date() if self.time_sync else date.today()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self._map = json.load(f)
            except Exception as e:
                print(f"[OperatorStationMap] Failed to load: {e}")
                self._map = self._map
        else:
            self._map = {}

    def _save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._map, f, indent=2)
        except Exception as e:
            print(f"[OperatorStationMap] Failed to save: {e}")

    def set(self, operator: str, station: str):
        self._load()
        self._map[operator] = station
        self._save()

    def get(self, operator: str) -> Optional[str]:
        self._load()
        return self._map.get(operator, "Unknown")

    def remove(self, operator: str):
        self._load()
        if operator in self._map:
            del self._map[operator]
            self._save()

    def as_dict(self) -> Dict[str, str]:
        self._load()
        return dict(self._map)

    def clear(self):
        self._map = {}
        self._save()

    def _get_last_cleared_date(self) -> Optional[date]:
        if os.path.exists(self.last_cleared_file):
            try:
                with open(self.last_cleared_file, "r", encoding="utf-8") as f:
                    date_str = f.read().strip()
                    return datetime.strptime(date_str, "%Y-%m-%d").date()
            except Exception as e:
                print(f"[OperatorStationMap] Failed to read last cleared date: {e}")
        return None

    def _set_last_cleared_date(self, d: date):
        try:
            with open(self.last_cleared_file, "w", encoding="utf-8") as f:
                f.write(d.strftime("%Y-%m-%d"))
        except Exception as e:
            print(f"[OperatorStationMap] Failed to write last cleared date: {e}")

    def daily_clear_if_needed(self):
        """
        Atomically clear the operator-station map if it hasn't been cleared today.
        This method is safe for multi-user/multi-device environments.
        """
        today = self._get_today()
        last_cleared = self._get_last_cleared_date()
        if last_cleared != today:
            self.clear()
            self._set_last_cleared_date(today)
            print(f"[OperatorStationMap] Cleared for new day: {today}")
        else:
            print(f"[OperatorStationMap] Already cleared today: {today}")
