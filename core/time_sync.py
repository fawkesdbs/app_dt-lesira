import time
import threading
import requests
from dateutil import parser
from datetime import datetime


class TimeSync:
    """
    Synchronizes local time with an online time API and provides a consistent, accurate current time.

    This class periodically synchronizes with an online time source and provides a thread-safe
    method to get the current time, adjusted for any drift since the last synchronization.

    :param resync_interval_minutes: How often (in minutes) to resynchronize with the online time source.
    :type resync_interval_minutes: int
    """

    def __init__(self, resync_interval_minutes=30):
        """
        Initialize the TimeSync object and start the background synchronization thread.

        :param resync_interval_minutes: How often (in minutes) to resynchronize with the online time source.
        :type resync_interval_minutes: int
        """
        self.sync_time = None
        self.local_reference = None
        self.lock = threading.Lock()
        self.resync_interval = resync_interval_minutes * 60
        self._stop_event = threading.Event()

        self.sync()

        self.thread = threading.Thread(target=self._resync_loop, daemon=True)
        self.thread.start()

    def sync(self):
        """
        Synchronize the local time reference with the online time API.

        Fetches the current time from https://timeapi.io for the Africa/Johannesburg timezone,
        and updates the internal reference points.

        :raises Exception: If the request to the time API fails or the response is invalid.
        """
        try:
            response = requests.get(
                "https://timeapi.io/api/Time/current/zone?timeZone=Africa/Johannesburg"
            )
            response.raise_for_status()
            data = response.json()
            new_sync_time = parser.isoparse(data["dateTime"])
            new_local_reference = datetime.now()

            with self.lock:
                self.sync_time = new_sync_time
                self.local_reference = new_local_reference

            print(
                f"[TimeSync] Synced at {new_local_reference}, online time: {new_sync_time}"
            )
        except Exception as e:
            print(f"[TimeSync] Sync failed: {e}")

    def _resync_loop(self):
        """
        Internal method: Background thread loop for periodic resynchronization.

        Sleeps for the configured interval and then calls :meth:`sync`.
        """
        while not self._stop_event.is_set():
            time.sleep(self.resync_interval)
            self.sync()

    def get_now(self):
        """
        Get the current synchronized time.

        Returns the current time, adjusted for drift since the last synchronization.
        If synchronization has not yet occurred, returns the local system time.

        :return: The current synchronized datetime.
        :rtype: datetime
        """
        with self.lock:
            if self.sync_time is None or self.local_reference is None:

                return datetime.now()
            delta = datetime.now() - self.local_reference
            return self.sync_time + delta

    def stop(self):
        """
        Stop the background synchronization thread.

        This method signals the background thread to terminate and waits for it to finish.
        """
        self._stop_event.set()
        self.thread.join()
