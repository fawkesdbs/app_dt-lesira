import os
import json
from datetime import datetime, date
from typing import Dict, Optional
from .time_sync import TimeSync


class OperatorStationMap:
    """
    Maintains a mapping between operators and their assigned stations, with persistent storage.

    This class provides methods to set, get, remove, and clear operator-station assignments,
    and ensures the mapping is persisted to disk. It also supports daily automatic clearing
    of the map, with optional time synchronization.

    :param log_dir_path: Directory where the mapping and metadata files are stored.
    :type log_dir_path: str
    :param filename: Name of the JSON file to store the mapping.
    :type filename: str, optional
    :param time_sync: Optional time synchronization utility.
    :type time_sync: Optional[TimeSync]
    """

    def __init__(
        self,
        log_dir_path: str,
        filename: str = "operator_station_map.json",
        time_sync: Optional[TimeSync] = None,
    ):
        """
        Initialize the OperatorStationMap.

        :param log_dir_path: Directory where the mapping and metadata files are stored.
        :type log_dir_path: str
        :param filename: Name of the JSON file to store the mapping.
        :type filename: str, optional
        :param time_sync: Optional time synchronization utility.
        :type time_sync: Optional[TimeSync]
        """
        self.file_path = os.path.join(log_dir_path, filename)
        self.last_cleared_file = os.path.join(
            log_dir_path, "operator_station_map_last_cleared.txt"
        )
        self._map: Dict[str, str] = {}
        self.time_sync = time_sync
        self._load()

    def _get_today(self) -> date:
        """
        Get today's date, using time synchronization if available.

        :return: Today's date.
        :rtype: date
        """
        return self.time_sync.get_now().date() if self.time_sync else date.today()

    def _load(self):
        """
        Load the operator-station map from disk, if it exists.
        """
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
        """
        Save the current operator-station map to disk.
        """
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._map, f, indent=2)
        except Exception as e:
            print(f"[OperatorStationMap] Failed to save: {e}")

    def set(self, operator: str, station: str):
        """
        Assign an operator to a station.

        :param operator: The operator's identifier.
        :type operator: str
        :param station: The station's identifier.
        :type station: str
        """
        self._load()
        self._map[operator] = station
        self._save()

    def get(self, operator: str) -> Optional[str]:
        """
        Retrieve the station assigned to an operator.

        :param operator: The operator's identifier.
        :type operator: str
        :return: The station assigned to the operator, or "Unknown" if not found.
        :rtype: Optional[str]
        """
        self._load()
        return self._map.get(operator, "Unknown")

    def remove(self, operator: str):
        """
        Remove an operator from the map.

        :param operator: The operator's identifier.
        :type operator: str
        """
        self._load()
        if operator in self._map:
            del self._map[operator]
            self._save()

    def as_dict(self) -> Dict[str, str]:
        """
        Get the current operator-station map as a dictionary.

        :return: A dictionary mapping operators to stations.
        :rtype: Dict[str, str]
        """
        self._load()
        return dict(self._map)

    def clear(self):
        """
        Clear all operator-station assignments and save the empty map.
        """
        self._map = {}
        self._save()

    def _get_last_cleared_date(self) -> Optional[date]:
        """
        Retrieve the date when the map was last cleared.

        :return: The date the map was last cleared, or None if not available.
        :rtype: Optional[date]
        """
        if os.path.exists(self.last_cleared_file):
            try:
                with open(self.last_cleared_file, "r", encoding="utf-8") as f:
                    date_str = f.read().strip()
                    return datetime.strptime(date_str, "%Y-%m-%d").date()
            except Exception as e:
                print(f"[OperatorStationMap] Failed to read last cleared date: {e}")
        return None

    def _set_last_cleared_date(self, date: date):
        """
        Set the date when the map was last cleared.

        :param date: The date to record as last cleared.
        :type date: date
        """
        try:
            with open(self.last_cleared_file, "w", encoding="utf-8") as f:
                f.write(date.strftime("%Y-%m-%d"))
        except Exception as e:
            print(f"[OperatorStationMap] Failed to write last cleared date: {e}")

    def daily_clear_if_needed(self):
        """
        Atomically clear the operator-station map if it hasn't been cleared today.

        This method is safe for multi-user/multi-device environments. It checks the last
        cleared date and only clears the map if it hasn't already been cleared today.
        """
        today = self._get_today()
        last_cleared = self._get_last_cleared_date()
        if last_cleared != today:
            self.clear()
            self._set_last_cleared_date(today)
            print(f"[OperatorStationMap] Cleared for new day: {today}")
        else:
            print(f"[OperatorStationMap] Already cleared today: {today}")
