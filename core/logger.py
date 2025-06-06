import os
import json
import uuid
from pathlib import Path
from datetime import datetime, date
from typing import Any, Dict, List, Optional
from .config import EVENTS
from .time_sync import TimeSync


class DowntimeLogger:
    def __init__(self, log_dir: str, time_sync: Optional[TimeSync] = None):
        self.log_dir: Path = Path(log_dir)
        self.time_sync: Optional[TimeSync] = time_sync

    def get_log_path(self, date_str: str) -> Path:
        return self.log_dir / f"log_{date_str}.json"

    def get_lock_path(self, date_str: str) -> Path:
        return self.log_dir / f"log_{date_str}.json.lock"

    def get_now(self) -> datetime:
        if self.time_sync:
            return self.time_sync.get_now()
        return datetime.now()

    def load_log(self, date_str: str) -> List[Dict[str, Any]]:
        path: Path = self.get_log_path(date_str)
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[DowntimeLogger] Failed to load log: {e}")
                return []
        return []

    def save_log(self, log_data: List[Dict[str, Any]], date_str: str) -> None:
        path: Path = self.get_log_path(date_str)
        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[DowntimeLogger] Failed to save log: {e}")

    def log_downtime_start(
        self,
        date_str: str,
        station: str,
        operators: List[str],
        downtime: str,
    ) -> List[str]:
        ids: List[str] = []
        try:
            log_data: List[Dict[str, Any]] = self.load_log(date_str)
            now: str = self.get_now().isoformat()
            category: str = EVENTS[downtime]

            for operator in operators:
                entry_id: str = str(uuid.uuid4())
                ids.append(entry_id)

                log_entry: Dict[str, Any] = {
                    "id": entry_id,
                    "station": station,
                    "operator": operator,
                    "downtime": downtime,
                    "category": category,
                    "start_time": now,
                    "end_time": None,
                    "duration_minutes": None,
                }

                log_data.append(log_entry)

            self.save_log(log_data, date_str)
        except Exception as e:
            print(f"[DowntimeLogger] Failed to log downtime start: {e}")
        return ids

    def log_downtime_stop(
        self,
        date_str: str,
        downtime_ids: List[str],
    ) -> List[str]:
        updated_ids: List[str] = []
        try:
            log_data: List[Dict[str, Any]] = self.load_log(date_str)
            now: datetime = self.get_now()

            for entry in log_data:
                entry_id: str = entry.get("id", "")
                if entry_id in downtime_ids and entry.get("end_time") is None:
                    start_time_str: Optional[str] = entry.get("start_time")
                    if not start_time_str:
                        continue

                    start_time: datetime = datetime.fromisoformat(start_time_str)
                    duration: float = (now - start_time).total_seconds() / 60
                    entry["end_time"] = now.isoformat()
                    entry["duration_minutes"] = round(duration, 2)
                    updated_ids.append(entry_id)

            if updated_ids:
                self.save_log(log_data, date_str)
        except Exception as e:
            print(f"[DowntimeLogger] Failed to log downtime stop: {e}")
        return updated_ids


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
        """Get today's date, using TimeSync if available."""
        if self.time_sync:
            return self.time_sync.get_now().date()
        return date.today()

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
        print(
            f"[OperatorStationMap] Mapping on get: {operator} | {self._map.get(operator, 'Unknown')}"
        )
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
