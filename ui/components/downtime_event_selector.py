import tkinter as tk
from collections import defaultdict
from typing import Dict, Callable


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
