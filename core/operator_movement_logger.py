from datetime import datetime
import mysql.connector as connector
from typing import Optional, List, Dict
from .time_sync import TimeSync


class OperatorMovementLogger:
    """
    Logs operator sign-in and sign-out events to daily JSON log files.
    """

    def __init__(self, db_config: dict, time_sync: Optional[TimeSync] = None):
        self.db_config = db_config
        self.time_sync = time_sync
        self.conn = connector.connect(**db_config)

    def _now(self) -> datetime:
        return self.time_sync.get_now() if self.time_sync else datetime.now()

    def log_event(self, operator: str, station: str, state: str) -> bool:
        """
        Log an operator sign-in or sign-out event to the daily log file.

        :param operator: Operator ID or name
        :param station: Station name
        :param state: "sign in" or "sign out"
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT state FROM operator_events "
            "WHERE operator=%s ORDER BY event_time DESC LIMIT 1",
            (operator,),
        )
        row = cursor.fetchone()
        if row and row[0] == state:
            print(f"[OperatorMovement] '{operator}' already '{state}'. Skipping.")
            cursor.close()
            return False

        cursor.execute(
            "INSERT INTO operator_events (operator, station, event_time, state) "
            "VALUES (%s, %s, %s, %s)",
            (operator, station, self._now().strftime("%Y-%m-%d %H:%M:%S"), state),
        )

        self.conn.commit()
        cursor.close()
        return True

    def load_log(self, date_str: str) -> List[dict]:
        """
        Return all events for a given date ('YYYY-MM-DD') as a list of dicts.
        """
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT operator, station, event_time AS time, state "
            "FROM operator_events "
            "WHERE DATE(event_time) = %s "
            "ORDER BY event_time ASC",
            (date_str,),
        )
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def get_current_station_map(self) -> Dict[str, str]:
        """
        Build and return {operator: station} for everyone whose latest event
        is a 'sign in'.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT e.operator, e.station
            FROM operator_events e
            JOIN (
                SELECT operator, MAX(event_time) AS latest
                FROM operator_events
                GROUP BY operator
            ) latest
                ON e.operator = latest.operator
                AND e.event_time = latest.latest
            WHERE e.state = 'sign in'
            """
        )
        result = {op: st for op, st in cursor.fetchall()}
        cursor.close()
        return result

    def close(self):
        self.conn.close()
