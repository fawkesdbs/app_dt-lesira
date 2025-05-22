import tkinter as tk
from tkinter import messagebox, ttk
from collections import defaultdict
import datetime
from typing import Dict, List, Callable, Optional
from config import station_names, EVENTS, OPERATORS
from components import CollapsibleLogFrame, DowntimeEventSelector
from state import AppState


def center_top_popup(parent: tk.Tk, popup: tk.Toplevel, width=400, y_offset=0):
    """
    Positions the popup horizontally centered and vertically aligned to the top of the parent window.
    """
    parent.update_idletasks()
    parent_x = parent.winfo_x()
    parent_y = parent.winfo_y()
    parent_width = parent.winfo_width()
    x = parent_x + (parent_width // 2) - (width // 2)
    y = parent_y + y_offset
    popup.geometry(f"{width}x{popup.winfo_height()}+{x}+{y}")


class DowntimeTrackerUI:
    def __init__(self, root: tk.Tk, state: AppState):
        self.root: tk.Tk = root
        self.state = state
        self.selected_station = tk.StringVar()
        self.selected_station.set(station_names[0])
        # Track all active downtimes: each is a dict with keys: station, event, operators (list)
        self.active_downtimes: List[Dict] = []
        self.summary_popup = None
        self._load_active_downtimes_from_log()
        self.setup_ui()

    def setup_ui(self) -> None:
        self.root.title(f"Downtime Tracker")
        self.root.resizable(False, False)
        self.width = 510
        self.height = 270
        screen_width = self.root.winfo_screenwidth()
        self.x = screen_width - self.width
        self.y = 0

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
        summary_btn.grid(row=0, column=2, sticky="W", padx=10, pady=5)

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

        # Collapsible log frame (expand/collapse for full log)
        self.log_frame = CollapsibleLogFrame(
            self.root, self.state, self, grid_row=3, grid_column=0
        )

        self.root.update_idletasks()
        self.root.geometry(f"{self.width}x{self.root.winfo_height()}+{self.x}+{self.y}")

    def resize(self) -> None:
        self.root.update_idletasks()
        self.root.geometry("")

    def on_start_downtime(self) -> None:
        modal = tk.Toplevel(self.root)
        modal.title("Start Downtime")
        modal.transient(self.root)
        modal.grab_set()
        modal.focus_set()

        tk.Label(
            modal,
            text=f"Station: {self.selected_station.get()}",
            font=("TkDefaultFont", 16),
        ).pack(pady=5)

        # Operator scan
        tk.Label(modal, text="Scan Operator IDs:").pack(pady=5)
        entry_frame = tk.Frame(modal)
        entry_frame.pack(pady=5)
        operator_entry = tk.Entry(entry_frame, width=20)
        operator_entry.grid(row=0, column=0, padx=5)
        operator_entry.focus_set()
        add_btn = tk.Button(entry_frame, text="Add", command=lambda: add_operator())
        add_btn.grid(row=0, column=1, padx=5)

        operator_listbox = tk.Listbox(modal, height=3, width=30)
        operator_listbox.pack(pady=5)
        operator_count = tk.Label(modal, text="No operators added.")
        operator_count.pack(pady=5)

        scanned_operators: List[str] = []

        def update_operator_list():
            operator_listbox.delete(0, tk.END)
            for op in scanned_operators:
                operator_listbox.insert(tk.END, op)

        def add_operator():
            op_id = operator_entry.get().strip()
            if op_id in OPERATORS:
                op_name = OPERATORS[op_id]
                # Check if operator is already in downtime (anywhere)
                if self.state.is_downtime_active(op_name):
                    messagebox.showerror(
                        "Already in Downtime",
                        f"{op_name} is already in a downtime and cannot be added to another.",
                    )
                elif op_name not in scanned_operators:
                    scanned_operators.append(op_name)
                    update_operator_list()
                    operator_count.config(
                        text=f"{len(scanned_operators)} operators added."
                    )
                    modal.update_idletasks()
                    center_top_popup(self.root, modal, width=400)
                else:
                    messagebox.showwarning("Duplicate", f"{op_name} already scanned.")
            else:
                messagebox.showerror(
                    "Invalid Operator", f"ID '{op_id}' not recognized."
                )
            operator_entry.delete(0, tk.END)
            operator_entry.focus_set()

        operator_entry.bind("<Return>", lambda event: add_operator())

        # Downtime event selection
        selected_event = tk.StringVar(modal)
        selected_event_label = tk.Label(modal, text="Selected Downtime Event: None")
        selected_event_label.pack(pady=5)

        def on_event_selected(event_name):
            selected_event.set(event_name)
            selected_event_label.config(text=f"Selected Downtime Event: {event_name}")

        tk.Button(
            modal,
            text="Choose Downtime Event",
            command=lambda: DowntimeEventSelector(modal, EVENTS, on_event_selected),
        ).pack(pady=5)

        def submit():
            if not scanned_operators:
                messagebox.showerror(
                    "Missing Operators", "Please scan at least one operator."
                )
                return
            if not selected_event.get():
                messagebox.showerror("Missing Event", "Please select a downtime event.")
                return
            # Final check before starting downtime
            already_in_downtime = self.state.can_start_downtime(scanned_operators)
            if already_in_downtime:
                messagebox.showerror(
                    "Operator(s) Already in Downtime",
                    f"The following operator(s) are already in downtime and cannot be added: {'\n'.join(already_in_downtime)}",
                )
                return
            event = selected_event.get()
            self.state.start_downtime(
                self.selected_station.get(), event, scanned_operators
            )
            # Track this downtime in the UI
            self.active_downtimes.append(
                {
                    "station": self.selected_station.get(),
                    "event": event,
                    "operators": scanned_operators.copy(),
                }
            )
            modal.destroy()
            messagebox.showinfo(
                "Downtime Started",
                f"Downtime '{event}' started for {'\n'.join(scanned_operators)}.",
            )
            self.log_frame.update_log_display()

        tk.Button(modal, text="Submit", command=submit).pack(pady=5)
        center_top_popup(
            self.root,
            modal,
            width=400,
        )

    def on_stop_downtime(self) -> None:
        # If there are no active downtimes, nothing to stop
        if not self.active_downtimes or all(
            len(dt["operators"]) == 0 for dt in self.active_downtimes
        ):
            messagebox.showwarning(
                "No Active Downtime", "No downtime is currently active."
            )
            return

        modal = tk.Toplevel(self.root)
        modal.title("Stop Downtime")
        modal.transient(self.root)
        modal.grab_set()
        modal.focus_set()

        tk.Label(
            modal, text="Scan Operator IDs to stop downtime:", font=("Arial", 12)
        ).pack(pady=10)
        entry_frame = tk.Frame(modal)
        entry_frame.pack(pady=5)
        operator_entry = tk.Entry(entry_frame, width=20)
        operator_entry.grid(row=0, column=0, padx=5)
        operator_entry.focus_set()
        add_btn = tk.Button(entry_frame, text="Add", command=lambda: add_operator())
        add_btn.grid(row=0, column=1, padx=5)

        operator_listbox = tk.Listbox(modal, height=3, width=30)
        operator_listbox.pack(pady=5)
        operator_count = tk.Label(modal, text="No operators added.")
        operator_count.pack(pady=5)

        scanned_operators: List[str] = []

        def update_operator_list():
            operator_listbox.delete(0, tk.END)
            for op in scanned_operators:
                operator_listbox.insert(tk.END, op)

        def add_operator():
            op_id = operator_entry.get().strip()
            if op_id in OPERATORS:
                op_name = OPERATORS[op_id]
                # Check if operator is in any active downtime
                if not self.state.is_downtime_active(op_name):
                    messagebox.showerror(
                        "Not in Downtime", f"{op_name} is not currently in downtime."
                    )
                elif op_name in scanned_operators:
                    messagebox.showwarning("Duplicate", f"{op_name} already scanned.")
                else:
                    scanned_operators.append(op_name)
                    update_operator_list()
                    operator_count.config(
                        text=f"{len(scanned_operators)} operators added."
                    )
            else:
                messagebox.showerror(
                    "Invalid Operator", f"ID '{op_id}' not recognized."
                )
            operator_entry.delete(0, tk.END)
            operator_entry.focus_set()

        operator_entry.bind("<Return>", lambda event: add_operator())

        def submit():
            if not scanned_operators:
                messagebox.showerror(
                    "Missing Operators", "Please scan at least one operator."
                )
                return
            # Stop downtime in state for only these operators
            self.state.stop_downtime(scanned_operators)
            # Remove these operators from any active downtime in the UI
            for op in scanned_operators:
                for dt in self.active_downtimes:
                    if op in dt["operators"]:
                        dt["operators"].remove(op)
            modal.destroy()
            messagebox.showinfo(
                "Downtime Ended", f"Downtime ended for {'\n'.join(scanned_operators)}."
            )
            # Optionally, remove empty downtime records from self.active_downtimes
            self.active_downtimes = [
                dt for dt in self.active_downtimes if dt["operators"]
            ]
            # No need to disable STOP button; user can always try to stop more, or see warning if none left
            self.log_frame.update_log_display()

        tk.Button(modal, text="Submit", command=submit).pack(pady=15)
        center_top_popup(self.root, modal, width=400)

    def show_operator_summary_popup(self):
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
        popup = tk.Toplevel(self.root)
        popup.title("Operator Downtime Summary")
        popup.transient(self.root)
        popup.grab_set()
        popup.focus_set()

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

        close_btn = tk.Button(popup, text="Close", command=popup.destroy)
        close_btn.pack(pady=5)

        popup.update_idletasks()
        center_top_popup(self.root, popup, width=400)

    def _load_active_downtimes_from_log(self):
        """
        Populate self.active_downtimes from open log entries (end_time is None).
        This ensures UI state matches persisted state after app restart.
        """
        # Get today's log entries
        log_entries = self.state.get_daily_log()
        # Group open downtimes by (station, event)
        open_downtimes = {}
        for entry in log_entries:
            # You may want to filter by current station only, or all stations
            if entry.get("end_time") is None:
                station = entry.get("station", "Unknown")
                event = entry.get("event", "Unknown")
                key = (station, event)
                if key not in open_downtimes:
                    open_downtimes[key] = {
                        "station": station,
                        "event": event,
                        "operators": [],
                    }
                op = entry.get("operator", "Unknown")
                open_downtimes[key]["operators"].append(op)
        # Convert to list
        self.active_downtimes = list(open_downtimes.values())
