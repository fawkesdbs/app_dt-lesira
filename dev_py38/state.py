from datetime import datetime
from typing import Any, Dict, List, Optional
from .logger import DowntimeLogger


class AppState:
    """
    Application state for downtime tracking.
    Ensures each operator can only be in one downtime at a time,
    but allows multiple concurrent downtimes for different stations/events.
    """

    def __init__(self, logger: DowntimeLogger):
        self.logger: DowntimeLogger = logger
        # Maps operator name to their current active downtime info
        self.active_downtimes: Dict[str, Dict[str, Optional[str]]] = {}

    def load_active_downtimes_from_log(self):
        """
        On startup, scan today's log for open downtimes and populate self.active_downtimes.
        """
        now: datetime = self.logger.get_now()
        date_str: str = now.strftime("%Y-%m-%d")
        raw_log: List[Dict[str, Any]] = self.logger.load_log(date_str)
        for entry in raw_log:
            if entry.get("end_time") is None:
                operator = entry.get("operator")
                event_id = entry.get("id")
                if operator and event_id:
                    self.active_downtimes[operator] = {
                        "id": event_id,
                        "date_str": date_str,
                    }

    def can_start_downtime(self, operators: List[str]) -> List[str]:
        """
        Returns a list of operators from the input who are already in an active downtime.
        Used to prevent an operator from being in multiple downtimes at once.
        """
        return [op for op in operators if op in self.active_downtimes]

    def is_downtime_active(self, operator: str) -> bool:
        """
        Returns True if the operator is currently in an active downtime.
        """
        return operator in self.active_downtimes

    def start_downtime(self, station: str, reason: str, operators: List[str]) -> None:
        """
        Starts a downtime for the given station, reason, and list of operators.
        Only operators not already in downtime should be passed in.
        """
        now: datetime = self.logger.get_now()
        date_str: str = now.strftime("%Y-%m-%d")
        ids: List[str] = self.logger.log_downtime_start(
            date_str, station, operators, reason
        )

        for operator, event_id in zip(operators, ids):
            self.active_downtimes[operator] = {
                "id": event_id,
                "date_str": date_str,
            }

    def stop_downtime(self, operators: List[str]) -> None:
        """
        Stops downtime for the given list of operators.
        Only operators currently in downtime should be passed in.
        """
        id_map: Dict[str, List[str]] = {}

        for operator in operators:
            info = self.active_downtimes.get(operator)
            if info and info["id"] and info["date_str"]:
                date_str = info["date_str"]
                if date_str not in id_map:
                    id_map[date_str] = []
                id_map[date_str].append(info["id"])

        for date_str, ids in id_map.items():
            self.logger.log_downtime_stop(date_str, ids)

        for operator in operators:
            self.active_downtimes.pop(operator, None)

    def get_daily_log(self) -> List[Dict[str, Any]]:
        """
        Returns a processed list of today's downtime log entries.
        """
        now: datetime = self.logger.get_now()
        date_str: str = now.strftime("%Y-%m-%d")
        raw_log: List[Dict[str, Any]] = self.logger.load_log(date_str)
        processed: List[Dict[str, Any]] = []

        for entry in raw_log:
            try:
                timestamp_str: str = entry.get("start_time") or ""
                timestamp: datetime = datetime.fromisoformat(timestamp_str)

                processed.append(
                    {
                        "timestamp": timestamp,
                        "category": entry.get("category", "Unknown"),
                        "event": entry.get("downtime", "Unknown"),
                        "operator": entry.get("operator", "Unknown"),
                        "station": entry.get("station", "Unknown"),
                        "end_time": entry.get("end_time", "Unknown"),
                        "duration_minutes": entry.get("duration_minutes", "Unknown"),
                    }
                )
            except Exception as e:
                print(f"[AppState] Skipping invalid log entry: {e}")
                continue

        processed.sort(key=lambda e: e["timestamp"])
        return processed
