import tkinter as tk
from tkinter import ttk, font
from .state import AppState
from collections import defaultdict
from typing import Dict, Callable


class CollapsibleLogFrame(ttk.Frame):
    def __init__(self, parent: tk.Tk, state: AppState, app_ui, **kwargs):
        grid_row = kwargs.pop("grid_row", 0)
        grid_column = kwargs.pop("grid_column", 0)

        super().__init__(parent, **kwargs)

        self.app_state = state
        self.app_ui = app_ui
        self.expanded = False

        self.grid(
            row=grid_row,
            column=grid_column,
            sticky="nsew",
            columnspan=3,
            pady=10,
            padx=10,
        )
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.header = tk.Frame(self)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.columnconfigure(1, weight=1)

        self.toggle_btn = tk.Button(
            self.header, text="▼ Show Full Log", command=self.toggle
        )
        self.toggle_btn.grid(row=0, column=0, sticky="w")

        self.current_label = tk.Label(self.header, text="", anchor="w")
        self.current_label.grid(row=0, column=1, sticky="ew", padx=10)

        self.tree_frame = tk.Frame(self)
        self.tree_frame.grid(row=1, column=0, sticky="nsew", pady=(5, 0))
        self.tree_frame.columnconfigure(0, weight=1)
        self.tree_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            self.tree_frame,
            columns=("Time", "Category", "Downtime", "Operator", "Status"),
            show="headings",
        )
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            if col == "Status":
                self.tree.column(col, anchor="center", width=50)
            else:
                self.tree.column(col, anchor="w", width=100)

        self.scrollbar = ttk.Scrollbar(
            self.tree_frame, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")

        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.tree_frame.grid_remove()

        self.tree.tag_configure("ended", foreground="#0b334c")
        self.tree.tag_configure("live", foreground="#042f04")
        # You can also set background if you want:
        self.tree.tag_configure("ended", background="#e5e5ff")
        # self.tree.tag_configure("live", background="#b2ff9b")

        self.update_log_display()

    def autosize_columns(self):
        for col in self.tree["columns"]:
            # max_width = font.Font().measure(col)

            # for item in self.tree.get_children():
            #     cell_value = str(self.tree.set(item, col))
            #     cell_width = font.Font().measure(cell_value)
            #     max_width = max(max_width, cell_width)

            self.tree.column(col, width=100)

    def toggle(self):
        self.expanded = not self.expanded
        if self.expanded:
            self.toggle_btn.config(text="▲ Hide Full Log")
            self.tree_frame.grid()
            self.master.update_idletasks()
        else:
            self.toggle_btn.config(text="▼ Show Full Log")
            self.tree_frame.grid_remove()
            self.master.update_idletasks()

        self.update_log_display()
        self.app_ui.resize()

    def update_log_display(self):
        selected_station = None
        if hasattr(self.app_ui, "selected_station"):
            selected_station = self.app_ui.selected_station.get()
        log = self.app_state.get_daily_log()
        if selected_station is not None:
            log = [entry for entry in log if entry.get("station") == selected_station]

        if log:
            last = log[-1]
            summary = f"{last['timestamp'].strftime('%H:%M:%S')} | {last['event']} ({last['operator']})"
        else:
            summary = "No downtimes logged today."

        self.current_label.config(text=summary)

        if self.expanded:
            self.tree.delete(*self.tree.get_children())
            for entry in log:
                status = entry.get("status", "").lower()
                tag = None
                if status == "live":
                    tag = "live"
                elif status == "✔️":
                    tag = "ended"
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        entry["timestamp"].strftime("%H:%M:%S"),
                        entry["category"],
                        entry["event"],
                        entry["operator"],
                        entry["status"],
                    ),
                    tags=(tag,),
                )
            self.autosize_columns()


class DowntimeEventSelector:
    def __init__(
        self,
        master: tk.Tk,
        events: Dict[str, list],
        callback: Callable[[str], None],
    ):
        self.master = master
        self.events = events
        self.callback = callback
        self.grouped_events = self._group_events()
        self._build_selector()

    def _group_events(self) -> Dict[str, list]:
        grouped = defaultdict(list)
        for event, category in self.events.items():
            grouped[category].append(event)
        return grouped

    def _build_selector(self):
        self.window = tk.Toplevel(self.master)
        self.master.update_idletasks()
        width = 400
        height = 320
        parent_x = self.master.winfo_x()
        parent_y = self.master.winfo_y()
        parent_width = self.master.winfo_width()
        x = parent_x + (parent_width // 2) - (width // 2)
        y = parent_y
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        self.window.title("Select Downtime Event")

        self.window.transient(self.master)
        self.window.grab_set()
        self.window.focus_set()

        tk.Label(self.window, text="Select Downtime Event:", font=("Arial", 12)).pack(
            pady=5
        )

        self.listbox = tk.Listbox(self.window, width=50, height=15)
        self.listbox.pack(padx=10, pady=10)

        # Populate grouped event list
        for category, events in self.grouped_events.items():
            self.listbox.insert(tk.END, category.upper())
            self.listbox.itemconfig(tk.END, foreground="gray", background="#e0e0e0")
            self.listbox.insert(tk.END, "-" * 40)
            self.listbox.itemconfig(tk.END, foreground="gray")
            for event in events:
                self.listbox.insert(tk.END, f"    {event}")

        self.listbox.bind("<Double-Button-1>", self._on_select)

        # tk.Button(self.window, text="Select", command=self._on_select).pack(pady=5)

    def _on_select(self, event=None):
        selection = self.listbox.curselection()
        if not selection:
            return
        value = self.listbox.get(selection)
        if value.strip() == "" or value.strip("-") == "" or value.isupper():
            return  # Ignore headings and dividers
        self.window.destroy()
        self.callback(value.strip())
