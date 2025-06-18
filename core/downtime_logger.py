import json
import uuid
import requests
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

    def __init__(
        self,
        log_dir: Path,
        time_sync: Optional[TimeSync] = None,
        server_url: Optional[str] = None,
    ):
        """
        Initialize the DowntimeLogger.

        Args:
            log_dir (str): Path to the directory where logs will be stored.
            time_sync (Optional[TimeSync]): Optional time synchronization utility.
        """
        self.log_dir = log_dir
        self.time_sync = time_sync
        self.server_url = server_url

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
        if self.server_url:
            try:
                resp = requests.get(
                    f"{self.server_url}/log", params={"date": date_str}, timeout=10
                )
                resp.raise_for_status()
                logs = resp.json()
                if isinstance(logs, list):
                    return logs
                print(f"[DowntimeLogger] Unexpected server response format for logs")
            except Exception as e:
                print(f"[DowntimeLogger] Failed to load logs from server: {e}")

        path: Path = self.get_log_path(date_str)
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[DowntimeLogger] Failed to load local log: {e}")
        return []

    def save_log(
        self, log_entries: List[Dict[str, Any]], date_str: str, mode: str = "append"
    ) -> None:
        """
        Save the log data for a specific date.

        Args:
            log_data (List[Dict[str, Any]]): List of log entries to save.
            date_str (str): Date string in 'YYYY-MM-DD' format.
        """
        if mode not in ("append", "update"):
            raise ValueError(f"Invalid mode {mode}, must be 'append' or 'update'")

        if not log_entries:
            return

        if self.server_url:
            for entry in log_entries:
                try:
                    if mode == "append":
                        resp = requests.post(
                            f"{self.server_url}/log", json=entry, timeout=10
                        )
                    else:
                        entry_id = entry.get("id")
                        if not entry_id:
                            print(
                                "[DowntimeLogger] Missing 'id' for update entry, skipping"
                            )
                            continue
                        resp = requests.put(
                            f"{self.server_url}/log/{entry_id}", json=entry, timeout=10
                        )

                    if resp.status_code != 200:
                        print(
                            f"[DowntimeLogger] Server rejected log entry: {resp.status_code} {resp.text}"
                        )
                except Exception as e:
                    print(f"[DowntimeLogger] Failed to send log entry to server: {e}")

        else:
            path = self.get_log_path(date_str)
            logs = []
            if path.exists():
                try:
                    with path.open("r", encoding="utf-8") as f:
                        logs = json.load(f)
                except Exception as e:
                    print(f"[DowntimeLogger] Failed to load local logs for saving: {e}")

            if mode == "append":
                logs.extend(log_entries)
            else:
                log_map = {entry.get("id"): entry for entry in logs if "id" in entry}
                for entry in log_entries:
                    eid = entry.get("id")
                    if eid:
                        log_map[eid] = entry
                logs = list(log_map.values())

            try:
                with path.open("w", encoding="utf-8") as f:
                    json.dump(logs, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[DowntimeLogger] Failed to save local logs: {e}")

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
            now: str = self.get_now().isoformat()
            category: str = EVENTS.get(downtime, "Unknown")

            for operator in operators:
                entry_id: str = str(uuid.uuid4())
                ids.append(entry_id)

                entry = {
                    "id": entry_id,
                    "station": station,
                    "operator": operator,
                    "downtime": downtime,
                    "category": category,
                    "start_time": now,
                    "end_time": None,
                    "duration_minutes": None,
                }
                self.save_log([entry], date_str, mode="append")
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

            log_map = {entry.get("id"): entry for entry in log_data if "id" in entry}

            entries_to_update = []

            for eid in downtime_ids:
                entry = log_map.get(eid)
                if entry and entry.get("end_time") is None:
                    start_time_str = entry.get("start_time")
                    if not start_time_str:
                        continue
                    start_time = datetime.fromisoformat(start_time_str)
                    duration = (now - start_time).total_seconds() / 60
                    entry["end_time"] = now.isoformat()
                    entry["duration_minutes"] = round(duration, 2)
                    entries_to_update.append(entry)
                    updated_ids.append(eid)

            if entries_to_update:
                self.save_log(entries_to_update, date_str, mode="update")
        except Exception as e:
            print(f"[DowntimeLogger] Failed to log downtime stop: {e}")
        return updated_ids
