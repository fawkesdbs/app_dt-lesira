from datetime import datetime
from typing import Any, Dict, List, Optional
from .downtime_logger import DowntimeLogger


class AppState:
    """
    Application state for downtime tracking.

    This class manages the state of operator downtimes, ensuring that each operator
    can only be in one downtime at a time, but allows multiple concurrent downtimes
    for different stations or events. It interacts with a DowntimeLogger to persist
    and retrieve downtime events.
    """

    def __init__(self, logger: DowntimeLogger):
        """
        Initialize the AppState.

        Args:
            logger (DowntimeLogger): The logger instance used for downtime event persistence.
        """
        self.logger: DowntimeLogger = logger
        self.active_downtimes: Dict[str, Dict[str, Optional[str]]] = {}

    def load_active_downtimes_from_log(self) -> None:
        """
        On startup, scan today's log for open downtimes and populate self.active_downtimes.

        This ensures that the application state is consistent with persisted logs,
        restoring any active downtimes that were not closed in a previous session.
        """
        now: datetime = self.logger.get_now()
        date_str: str = now.strftime("%Y-%m-%d")
        raw_log: List[Dict[str, Any]] = self.logger.load_log(date_str)
        self.active_downtimes.clear()
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

        Args:
            operators (List[str]): List of operator names to check.

        Returns:
            List[str]: Operators who are already in an active downtime.
        """
        return [op for op in operators if op in self.active_downtimes]

    def is_downtime_active(self, operator: str) -> bool:
        """
        Returns True if the operator is currently in an active downtime.

        Args:
            operator (str): The operator name.

        Returns:
            bool: True if the operator is in an active downtime, False otherwise.
        """
        return operator in self.active_downtimes

    def start_downtime(self, station: str, reason: str, operators: List[str]) -> None:
        """
        Starts a downtime for the given station, reason, and list of operators.

        Only operators not already in downtime should be passed in.

        Args:
            station (str): The station where downtime is being logged.
            reason (str): The reason/event for the downtime.
            operators (List[str]): List of operator names to start downtime for.
        """
        now: datetime = self.logger.get_now()
        date_str: str = now.strftime("%Y-%m-%d")
        ids: List[str] = self.logger.log_downtime_start(station, operators, reason)

        for operator, event_id in zip(operators, ids):
            self.active_downtimes[operator] = {
                "id": event_id,
                "date_str": date_str,
            }

    def stop_downtime(self, operators: List[str]) -> None:
        """
        Stops downtime for the given list of operators.

        Only operators currently in downtime should be passed in.

        Args:
            operators (List[str]): List of operator names to stop downtime for.
        """
        downtime_ids: List[str] = []
        for operator in operators:
            info = self.active_downtimes.get(operator)
            if info and info.get("id"):
                downtime_ids.append(info["id"])

        if downtime_ids:
            self.logger.log_downtime_stop(downtime_ids)

        for operator in operators:
            self.active_downtimes.pop(operator, None)

    def get_daily_log(self) -> List[Dict[str, Any]]:
        """
        Returns a processed list of today's downtime log entries.

        Each entry includes timestamp, category, event, operator, station,
        end time, duration, and status.

        :return: List of processed downtime log entries for today.
        :rtype: List[Dict[str, Any]]
        """
        now: datetime = self.logger.get_now()
        date_str: str = now.strftime("%Y-%m-%d")
        raw_log: List[Dict[str, Any]] = self.logger.load_log(date_str)
        processed: List[Dict[str, Any]] = []

        for entry in raw_log:
            try:
                timestamp_str: str = entry.get("start_time")
                # Only parse if it's a string
                if isinstance(timestamp_str, str):
                    timestamp = datetime.fromisoformat(timestamp_str)
                else:
                    timestamp = timestamp_str  # Already a datetime object
                end_time = entry.get("end_time")
                status = "Live" if not end_time else "✔️"

                processed.append(
                    {
                        "timestamp": timestamp,
                        "category": entry.get("category", "Unknown"),
                        "event": entry.get("downtime", "Unknown"),
                        "operator": entry.get("operator", "Unknown"),
                        "station": entry.get("station", "Unknown"),
                        "end_time": entry.get("end_time", "Unknown"),
                        "duration_minutes": entry.get("duration_minutes", "Unknown"),
                        "status": status,
                    }
                )
            except Exception as e:
                print(f"[AppState] Skipping invalid log entry: {e}")
                continue

        processed.sort(key=lambda e: e["timestamp"])
        return processed
