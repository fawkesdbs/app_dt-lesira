import tkinter as tk
from tkinter import ttk
from core.app_state import AppState


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

        self.tree.tag_configure("ended", background="#e5e5ff")
        self.tree.tag_configure("live", foreground="#042f04", background="#e5ffe5")
        self.tree.tag_configure("ended", background="#fffd6a")

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
