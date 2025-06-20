import os
import tkinter as tk
from tkinter import ttk
from collections import defaultdict
import datetime
from typing import Dict, List, Optional
from core.config import log_dir_path, station_names, EVENTS, OPERATORS
from core.app_state import AppState
from core.operator_movement_logger import OperatorMovementLogger
from core.time_sync import TimeSync
from .components.collapsible_log_frame import CollapsibleLogFrame
from .components.downtime_event_selector import DowntimeEventSelector
from .helpers import (
    center_top_popup,
    make_modal,
    show_error,
    show_info,
    show_warning,
    make_operator_scanner,
    show_operator_modal,
)


class DowntimeTrackerUI:
    """
    Main UI class for the Downtime Tracker application.

    This class manages the main window, event handling, operator sign-in/out,
    downtime logging, and summary popups.

    :param root: The root Tkinter window.
    :type root: tk.Tk
    :param app_state: The application state object for downtime tracking.
    :type app_state: AppState
    :param time_sync: Optional time synchronization utility.
    :type time_sync: Optional[TimeSync]
    """

    def __init__(
        self, root: tk.Tk, app_state: AppState, time_sync: Optional[TimeSync] = None
    ):
        """
        Initialize the DowntimeTrackerUI.

        :param root: The root Tkinter window.
        :type root: tk.Tk
        :param app_state: The application state object for downtime tracking.
        :type app_state: AppState
        :param time_sync: Optional time synchronization utility.
        :type time_sync: Optional[TimeSync]
        """
        self.root = root
        self.state = app_state
        self.time_sync = time_sync
        self.selected_station = tk.StringVar(value=station_names[0])
        self.active_downtimes: List[Dict] = []
        self.summary_popup = None
        movement_dir = os.path.normpath(
            os.path.join(os.path.dirname(log_dir_path), "movement")
        )
        os.makedirs(movement_dir, exist_ok=True)

        self.operator_movement_logger = OperatorMovementLogger(
            movement_dir, self.time_sync
        )
        self._load_active_downtimes_from_log()
        self._setup_ui()

    def _setup_ui(self) -> None:
        """
        Set up the main UI layout, widgets, and event bindings.
        """
        self.root.title("Downtime Tracker")
        self.root.resizable(False, False)
        self.width = 510
        self.height = 270

        header_frame = ttk.Frame(self.root)
        header_frame.grid(row=0, column=0, columnspan=3, sticky="W", padx=10, pady=5)

        ttk.Label(header_frame, text="Station:").grid(
            row=0, column=0, sticky="W", padx=10, pady=5
        )
        station_selector = ttk.Combobox(
            header_frame,
            textvariable=self.selected_station,
            values=station_names,
            state="readonly",
            width=15,
        )
        station_selector.grid(row=0, column=1, sticky="EW", padx=10, pady=5)
        station_selector.bind(
            "<<ComboboxSelected>>", lambda e: self.log_frame.update_log_display()
        )

        summary_btn = tk.Button(
            header_frame,
            text="Operator Summary",
            command=self.show_operator_summary_popup,
        )
        summary_btn.grid(row=0, column=2, sticky="W", padx=5, pady=5)

        signin_btn = tk.Button(
            header_frame,
            text="  In  ",
            command=self.on_sign_in,
            background="#4CAF50",
            foreground="#ffffff",
        )
        signin_btn.grid(row=0, column=3, sticky="W", padx=(80, 5), pady=5)

        signout_btn = tk.Button(
            header_frame,
            text="Out",
            command=self.on_sign_out,
            background="#f44336",
            foreground="#ffffff",
        )
        signout_btn.grid(row=0, column=4, sticky="W", padx=5, pady=5)

        events_frame = tk.LabelFrame(self.root, text="Downtime Control")
        events_frame.grid(row=1, column=0, padx=10, pady=5, columnspan=3, sticky="W")

        self.btn_start = tk.Button(
            events_frame,
            text="START Downtime",
            command=self.on_start_downtime,
            width=30,
            height=4,
        )
        self.btn_stop = tk.Button(
            events_frame,
            text="STOP Downtime",
            command=self.on_stop_downtime,
            width=30,
            height=4,
        )
        self.btn_start.grid(row=0, column=0, padx=10, pady=10)
        self.btn_stop.grid(row=0, column=1, padx=10, pady=10)

        self.log_frame = CollapsibleLogFrame(
            self.root, self.state, self, grid_row=3, grid_column=0
        )

        self.root.update_idletasks()
        self.root.geometry(f"{self.width}x{self.root.winfo_height()}")

    def _load_active_downtimes_from_log(self):
        """
        Populate self.active_downtimes from open log entries (where end_time is None).

        This ensures UI state matches persisted state after app restart.
        """
        log_entries = self.state.get_daily_log()
        open_downtimes = {}
        for entry in log_entries:
            if entry.get("end_time") is None:
                key = (entry.get("station", "Unknown"), entry.get("event", "Unknown"))
                if key not in open_downtimes:
                    open_downtimes[key] = {
                        "station": entry.get("station", "Unknown"),
                        "event": entry.get("event", "Unknown"),
                        "operators": [],
                    }
                open_downtimes[key]["operators"].append(
                    entry.get("operator", "Unknown")
                )
        self.active_downtimes = list(open_downtimes.values())

    def on_sign_in(self):
        """
        Handle the operator sign-in process, including scanning operator IDs and updating the map.
        """

        def submit(scanned_operators: List[str], modal: tk.Toplevel):
            """
            Submit the sign-in form, updating the operator-station map and closing any open 'Operator move' downtimes.
            """
            if not scanned_operators:
                show_error("Missing Operators", "Please scan at least one operator.")
                return
            station = self.selected_station.get()
            log = self.state.get_daily_log()
            for op in scanned_operators:
                for entry in reversed(log):  # Most recent first
                    if (
                        entry["operator"] == op
                        and entry["event"] == "Operator move"
                        and entry["status"] == "Live"
                    ):
                        self.state.stop_downtime([op])
                        break
                self.operator_movement_logger.log_event(op, station, state="Sign In")
            modal.destroy()
            op_str = "\n".join(scanned_operators)
            show_info(
                "Sign In Complete",
                f"The following operators have signed in to {station}:\n{op_str}",
            )

        show_operator_modal(
            self.root,
            self.selected_station.get(),
            "Sign In to Station",
            "Scan Operator IDs to sign in:",
            OPERATORS,
            submit,
        )

    def on_sign_out(self):
        """
        Handle the operator sign-out process, including scanning operator IDs and updating the map.
        """

        def submit(scanned_operators: List[str], modal: tk.Toplevel):
            """
            Submit the sign-out form, removing operators from the map.
            """
            if not scanned_operators:
                show_error("Missing Operators", "Please scan at least one operator.")
                return
            for op in scanned_operators:
                self.operator_station_map.remove(op)
                self.operator_movement_logger.log_event(
                    op, self.selected_station.get(), state="Sign Out"
                )
            modal.destroy()
            op_str = "\n".join(scanned_operators)
            show_info(
                "Sign Out Complete",
                f"The following operators have signed out:\n{op_str}",
            )

        show_operator_modal(
            self.root,
            self.selected_station.get(),
            "Sign Out to Station",
            "Scan Operator IDs to sign out:",
            OPERATORS,
            submit,
        )

    def on_start_downtime(self) -> None:
        """
        Handle the process of starting a downtime event, including operator scanning and event selection.
        """
        modal = make_modal(self.root, "Start Downtime")

        tk.Label(
            modal,
            text=f"Station: {self.selected_station.get()}",
            font=("TkDefaultFont", 16),
        ).pack(pady=5)

        tk.Label(modal, text="Scan Operator IDs:").pack(pady=5)
        entry_frame = tk.Frame(modal)
        entry_frame.pack(pady=5)
        operator_entry = tk.Entry(entry_frame, width=20)
        operator_entry.grid(row=0, column=0, padx=5)
        operator_entry.focus_set()

        operator_listbox = tk.Listbox(modal, height=3, width=30)
        operator_listbox.pack(pady=5)
        operator_count = tk.Label(modal, text="No operators added.")
        operator_count.pack(pady=5)

        scanned_operators: List[str] = []

        add_operator = make_operator_scanner(
            operator_entry,
            operator_listbox,
            operator_count,
            scanned_operators,
            OPERATORS,
        )
        operator_entry.bind("<Return>", lambda event: add_operator())

        selected_event = tk.StringVar(modal)
        selected_event_label = tk.Label(modal, text="Selected Downtime Event: None")
        selected_event_label.pack(pady=5)

        def on_event_selected(event_name):
            selected_event.set(event_name)
            selected_event_label.config(text=f"Selected Downtime Event: {event_name}")

        tk.Button(
            modal,
            text="Choose Downtime",
            command=lambda: DowntimeEventSelector(modal, EVENTS, on_event_selected),
            background="#626aff",
            foreground="#ffffff",
        ).pack(pady=5)

        def submit():
            """
            Submit the downtime start form, handling operator moves and event logging.
            """
            if not scanned_operators:
                show_error("Missing Operators", "Please scan at least one operator.")
                return
            if not selected_event.get():
                show_error("Missing Event", "Please select a downtime event.")
                return

            not_signed_in = [
                op
                for op in scanned_operators
                if self.operator_station_map.get(op) == "Unknown"
            ]
            if not_signed_in:
                op_str = "\n".join(not_signed_in)
                show_error(
                    "Operator Not Signed In",
                    f"The following operator(s) must be signed in to start downtime:\n{op_str}",
                )
                return

            event = selected_event.get()
            operator_station = {}
            if event == "Operator move":
                not_signed_in = [
                    op
                    for op in scanned_operators
                    if self.operator_station_map.get(op) == "Unknown"
                ]
                if not_signed_in:
                    op_str = "\n".join(not_signed_in)
                    show_error(
                        "Operator Not Signed In",
                        f"The following operator(s) must be signed in to log movement:\n{op_str}",
                    )
                    return

                already_in_downtime = self.state.can_start_downtime(scanned_operators)
                if already_in_downtime:
                    self.state.stop_downtime(already_in_downtime)
                    op_str = "\n".join(already_in_downtime)
                    show_info(
                        "Previous Downtime Ended",
                        f"Previous downtime(s) for the following operator(s) were automatically ended: \n{op_str}",
                    )
                    for op in already_in_downtime:
                        for dt in self.active_downtimes:
                            if op in dt["operators"]:
                                dt["operators"].remove(op)
                    self.active_downtimes = [
                        dt for dt in self.active_downtimes if dt["operators"]
                    ]
                # Remove operator from map for Operator Move, and record previous station
                for op in scanned_operators:
                    prev_station = self.operator_station_map.get(op)
                    operator_station[op] = prev_station
                    self.operator_station_map.remove(op)
                    self.operator_movement_logger.log_event(
                        op, prev_station, state="Sign Out"
                    )
                # Start downtime for 'Operator move'
                for op, prev_station in operator_station.items():
                    # You may need to update your logger/state to accept extra fields
                    self.state.start_downtime(prev_station, event, [op])
                    self.active_downtimes.append(
                        {
                            "station": prev_station,
                            "event": event,
                            "operators": [op],
                        }
                    )
                modal.destroy()
                op_str = "\n".join(scanned_operators)
                show_info(
                    "Downtime Started",
                    f"Downtime '{event}' started for: \n{op_str}.",
                )
                self._load_active_downtimes_from_log()
                self.log_frame.update_log_display()
                return

            else:
                already_in_downtime = self.state.can_start_downtime(scanned_operators)
                if already_in_downtime:
                    self.state.stop_downtime(already_in_downtime)
                    op_str = "\n".join(already_in_downtime)
                    show_info(
                        "Previous Downtime Ended",
                        f"Previous downtime(s) for the following operator(s) were automatically ended: \n{op_str}",
                    )
                    for op in already_in_downtime:
                        for dt in self.active_downtimes:
                            if op in dt["operators"]:
                                dt["operators"].remove(op)
                    self.active_downtimes = [
                        dt for dt in self.active_downtimes if dt["operators"]
                    ]
                for op in scanned_operators:
                    # If not mapped, add to map with current station
                    if self.operator_station_map.get(op) == "Unknown":
                        self.operator_station_map.set(op, self.selected_station.get())
                    operator_station[op] = self.operator_station_map.get(op)

            for op, station in operator_station.items():
                self.state.start_downtime(station, event, [op])
                self.active_downtimes.append(
                    {
                        "station": station,
                        "event": event,
                        "operators": [op],
                    }
                )
            modal.destroy()
            op_str = "\n".join(scanned_operators)
            show_info(
                "Downtime Started",
                f"Downtime '{event}' started for: \n{op_str}.",
            )
            self._load_active_downtimes_from_log()
            self.log_frame.update_log_display()

        tk.Button(
            modal,
            text="Submit",
            command=submit,
            background="#5E5E5E",
            foreground="#ffffff",
        ).pack(pady=5)
        center_top_popup(self.root, modal, width=400)

    def on_stop_downtime(self) -> None:
        """
        Handle the process of stopping downtime for scanned operators.

        :return: None
        """
        # If there are no active downtimes, nothing to stop
        if not self.active_downtimes or all(
            len(dt["operators"]) == 0 for dt in self.active_downtimes
        ):
            show_warning("No Active Downtime", "No downtime is currently active.")
            return

        def submit(scanned_operators: List[str], modal: tk.Toplevel):
            """
            Submit the downtime stop form, ending downtime for scanned operators.
            """
            if not scanned_operators:
                show_error("Missing Operators", "Please scan at least one operator.")
                return
            # Stop downtime in state for only these operators
            self.state.stop_downtime(scanned_operators)
            # Remove these operators from any active downtime in the UI
            for op in scanned_operators:
                for dt in self.active_downtimes:
                    if op in dt["operators"]:
                        dt["operators"].remove(op)
            # Optionally, remove empty downtime records from self.active_downtimes
            self.active_downtimes = [
                dt for dt in self.active_downtimes if dt["operators"]
            ]
            modal.destroy()
            op_str = "\n".join(scanned_operators)
            show_info("Downtime Ended", f"Downtime ended for \n{op_str}.")
            # No need to disable STOP button; user can always try to stop more, or see warning if none left
            self._load_active_downtimes_from_log()
            self.log_frame.update_log_display()

        show_operator_modal(
            self.root,
            self.selected_station.get(),
            "Stop Downtime",
            "Scan Operator IDs to stop downtime:",
            OPERATORS,
            submit,
        )

    def show_operator_summary_popup(self):
        """
        Show a popup window summarizing total downtime minutes per operator for the current day.
        """
        log = self.state.get_daily_log()
        operator_minutes = defaultdict(float)
        operator_counts = defaultdict(int)
        now = datetime.datetime.now()

        for entry in log:
            op = entry["operator"]
            # If log is closed, use duration_minutes
            if entry.get("end_time"):
                duration = entry.get("duration_minutes", 0.0)
            else:
                # Open log: calculate duration up to now
                start_time = entry["timestamp"]
                duration = (now - start_time).total_seconds() / 60

            operator_minutes[op] += duration
            operator_counts[op] += 1

        # Prepare summary data
        summary = []
        for op in sorted(operator_minutes.keys()):
            total_minutes = operator_minutes[op]
            count = operator_counts[op]
            summary.append((op, f"{total_minutes:.1f}", count))

        # Show popup
        popup = make_modal(self.root, "Operator Downtime Summary")

        tree = ttk.Treeview(
            popup,
            columns=("Operator", "Total Downtime (min)"),
            show="headings",
            height=10,
        )
        for col in ("Operator", "Total Downtime (min)"):
            tree.heading(col, text=col)
            tree.column(col, anchor="w", width=120)
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        for op, total, count in summary:
            tree.insert("", "end", values=(op, total))

        tk.Button(
            popup, text="Close", command=popup.destroy, background="#ff6d6d"
        ).pack(pady=5)
        center_top_popup(self.root, popup, width=400)

    def resize(self) -> None:
        """
        Resize the main window to fit its contents
        """
        self.root.update_idletasks()
        self.root.geometry("")
