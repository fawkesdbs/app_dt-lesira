import time
import threading
import requests
from dateutil import parser
from datetime import datetime


class TimeSync:
    def __init__(self, resync_interval_minutes=30):
        self.sync_time = None
        self.local_reference = None
        self.lock = threading.Lock()
        self.resync_interval = resync_interval_minutes * 60
        self._stop_event = threading.Event()

        self.sync()

        self.thread = threading.Thread(target=self._resync_loop, daemon=True)
        self.thread.start()

    def sync(self):
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
        while not self._stop_event.is_set():
            time.sleep(self.resync_interval)
            self.sync()

    def get_now(self):
        with self.lock:
            if self.sync_time is None or self.local_reference is None:

                return datetime.now()
            delta = datetime.now() - self.local_reference
            return self.sync_time + delta

    def stop(self):
        self._stop_event.set()
        self.thread.join()
