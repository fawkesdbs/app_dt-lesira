import mysql.connector as connector
import uuid
from datetime import datetime
from typing import List, Optional
from .config import EVENTS
from .time_sync import TimeSync


class DowntimeLogger:
    """
    Handles logging of downtime events to JSON files, including starting and stopping
    downtimes, and loading/saving logs. Optionally supports time synchronization.

    Attributes:
        db_config (dict): Dict with MySQL connection params
        time_sync (Optional[TimeSync]): Optional time synchronization utility.
    """

    def __init__(
        self,
        db_config: dict,
        time_sync: Optional[TimeSync] = None,
        server_url: Optional[str] = None,
    ):
        """
        Initialize the DowntimeLogger.

        Args:
            db_config (dict): Dict with MySQL connection params
            time_sync (Optional[TimeSync]): Optional time synchronization utility.
        """
        self.db_config = db_config
        self.time_sync = time_sync
        self.conn = connector.connect(**db_config)

    def get_now(self) -> datetime:
        """
        Get the current datetime, using time synchronization if available.

        Returns:
            datetime: The current datetime.
        """
        return self.time_sync.get_now() if self.time_sync else datetime.now()

    def load_log(self, date_str: str) -> List[dict]:
        """
        Load all downtime entries for the specified date.

        :param date_str: Date in 'YYYY-MM-DD' format
        :return: List of downtime event dicts
        """
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, station, operator, downtime, category,
                   start_time, end_time, duration_minutes
            FROM downtime_logs
            WHERE DATE(start_time) = %s
            ORDER BY start_time ASC
            """,
            (date_str,),
        )
        rows = cursor.fetchall()
        cursor.close()
        return rows if rows else []

    def log_downtime_start(
        self,
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
        now: str = self.get_now()
        category: str = EVENTS.get(downtime, "Unknown")
        cursor = self.conn.cursor()

        for operator in operators:
            entry_id: str = str(uuid.uuid4())
            ids.append(entry_id)

            cursor.execute(
                """
                INSERT INTO downtime_logs
                (id, station, operator, downtime, category, start_time)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (entry_id, station, operator, downtime, category, now),
            )
        self.conn.commit()
        cursor.close()
        return ids

    def log_downtime_stop(
        self,
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
        now: datetime = self.get_now()
        cursor = self.conn.cursor(dictionary=True)
        format_strings = ",".join(["%s"] * len(downtime_ids))
        cursor.execute(
            f"SELECT id, start_time, end_time FROM downtime_logs WHERE id IN ({format_strings})",
            downtime_ids,
        )
        rows = cursor.fetchall()

        for row in rows:
            if row["end_time"] is None:
                start_time = row["start_time"]
                duration_minutes = (now - start_time).total_seconds() / 60
                cursor.execute(
                    """
                    UPDATE downtime_logs
                    SET end_time=%s, duration_minutes=%s
                    WHERE id=%s
                    """,
                    (now, round(duration_minutes, 2), row["id"]),
                )
                updated_ids.append(row["id"])
        self.conn.commit()
        cursor.close()
        return updated_ids

    def close(self):
        self.conn.close()
