import tkinter as tk
from tkinter import messagebox
from typing import List, Optional, Dict, Callable


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
    popup.update_idletasks()
    popup.geometry(f"{width}x{popup.winfo_height()}+{x}+{y}")


def make_modal(root, title):
    modal = tk.Toplevel(root)
    modal.title(title)
    modal.transient(root)
    modal.grab_set()
    modal.focus_set()
    return modal


def show_error(title, msg):
    messagebox.showerror(title, msg)


def show_info(title, msg):
    messagebox.showinfo(title, msg)


def show_warning(title, msg):
    messagebox.showwarning(title, msg)


def make_operator_scanner(
    entry: tk.Entry,
    listbox: tk.Listbox,
    label: tk.Label,
    scanned_list: List[str],
    operator_map: Dict[str, str],
    on_add: Optional[Callable[[str], None]] = None,
    error_if_missing: bool = True,
) -> Callable[[], None]:
    def update_listbox():
        listbox.delete(0, tk.END)
        for op in scanned_list:
            listbox.insert(tk.END, op)

    def add_operator():
        op_id = entry.get().strip()
        if op_id in operator_map:
            op_name = operator_map[op_id]
            if op_name not in scanned_list:
                scanned_list.append(op_name)
                update_listbox()
                label.config(text=f"{len(scanned_list)} operators added.")
                if on_add:
                    on_add(op_name)
            else:
                show_warning("Duplicate", f"{op_name} already scanned.")
        else:
            if error_if_missing:
                show_error("Invalid Operator", f"ID '{op_id}' not recognized.")
        entry.delete(0, tk.END)
        entry.focus_set()

    return add_operator
