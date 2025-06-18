import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
from .config import EVENTS
from .time_sync import TimeSync


class DowntimeLogger:
    """
    Handles logging of downtime events to JSON files, including starting and stopping
    downtimes, and loading/saving logs. Optionally supports time synchronization.

    Attributes:
        log_dir (Path): Directory where log files are stored.
        time_sync (Optional[TimeSync]): Optional time synchronization utility.
    """

    def __init__(self, log_dir: Path, time_sync: Optional[TimeSync] = None):
        """
        Initialize the DowntimeLogger.

        Args:
            log_dir (str): Path to the directory where logs will be stored.
            time_sync (Optional[TimeSync]): Optional time synchronization utility.
        """
        self.log_dir: Path = log_dir
        self.time_sync: Optional[TimeSync] = time_sync

    def get_log_path(self, date_str: str) -> Path:
        """
        Get the path to the log file for a specific date.

        Args:
            date_str (str): Date string in 'YYYY-MM-DD' format.

        Returns:
            Path: Path to the log file.
        """
        return self.log_dir / f"log_{date_str}.json"

    def get_now(self) -> datetime:
        """
        Get the current datetime, using time synchronization if available.

        Returns:
            datetime: The current datetime.
        """
        if self.time_sync:
            return self.time_sync.get_now()
        return datetime.now()

    def load_log(self, date_str: str) -> List[Dict[str, Any]]:
        """
        Load the log entries for a specific date.

        Args:
            date_str (str): Date string in 'YYYY-MM-DD' format.

        :return: List of log entries for the date.
        :rtype: List[Dict[str, Any]]
        """
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
        """
        Save the log data for a specific date.

        Args:
            log_data (List[Dict[str, Any]]): List of log entries to save.
            date_str (str): Date string in 'YYYY-MM-DD' format.
        """
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
        """
        Log the start of a downtime event for one or more operators.

        Args:
            date_str (str): Date string in 'YYYY-MM-DD' format.
            station (str): Name of the station where downtime occurred.
            operators (List[str]): List of operator names.
            downtime (str): Downtime event/reason.

        Returns:
            List[str]: List of generated downtime entry IDs for each operator.
        """
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
        """
        Log the stop of downtime events for the given IDs, updating end time and duration.

        Args:
            date_str (str): Date string in 'YYYY-MM-DD' format.
            downtime_ids (List[str]): List of downtime entry IDs to stop.

        Returns:
            List[str]: List of IDs that were successfully updated.
        """
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
