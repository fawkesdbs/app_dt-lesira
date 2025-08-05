import tkinter as tk
from tkinter import messagebox
from typing import List, Optional, Dict, Callable


def center_top_popup(parent: tk.Tk, popup: tk.Toplevel, width=400, y_offset=0):
    """
    Position the popup window horizontally centered and vertically aligned to the top of the parent window.

    :param parent: The parent Tkinter root window.
    :type parent: tk.Tk
    :param popup: The popup window to position.
    :type popup: tk.Toplevel
    :param width: The width of the popup window in pixels. Defaults to 400.
    :type width: int, optional
    :param y_offset: The vertical offset from the top of the parent window. Defaults to 0.
    :type y_offset: int, optional
    :return: None
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
    """
    Create and configure a modal dialog window.

    :param root: The parent Tkinter root window.
    :type root: tk.Tk
    :param title: The title for the modal window.
    :type title: str
    :return: The created modal Toplevel window.
    :rtype: tk.Toplevel
    """
    modal = tk.Toplevel(root)
    modal.title(title)
    modal.transient(root)
    modal.grab_set()
    modal.focus_set()
    return modal


def show_error(title, msg):
    """
    Display an error message box.

    :param title: The title of the error dialog.
    :type title: str
    :param msg: The error message to display.
    :type msg: str
    :return: None
    """
    messagebox.showerror(title, msg)


def show_info(title, msg):
    """
    Display an informational message box.

    :param title: The title of the info dialog.
    :type title: str
    :param msg: The informational message to display.
    :type msg: str
    :return: None
    """
    messagebox.showinfo(title, msg)


def show_warning(title, msg):
    """
    Display a warning message box.

    :param title: The title of the warning dialog.
    :type title: str
    :param msg: The warning message to display.
    :type msg: str
    :return: None
    """
    messagebox.showwarning(title, msg)


def make_operator_scanner(
    entry: tk.Entry,
    listbox: tk.Listbox,
    label: tk.Label,
    scanned_list: List[str],
    operator_map: Dict[str, str],
    on_add: Optional[Callable[[str], None]] = None,
) -> Callable[[], None]:
    """
    Create a function that scans and adds operator IDs from an entry widget to a listbox.

    The returned function reads the operator ID from the entry, checks it against the operator map,
    adds the corresponding operator name to the scanned list and listbox if valid, and updates the label.
    Optionally calls a callback on successful addition and shows error/warning dialogs as needed.

    :param entry: The Tkinter Entry widget for operator ID input.
    :type entry: tk.Entry
    :param listbox: The Tkinter Listbox widget to display scanned operators.
    :type listbox: tk.Listbox
    :param label: The Tkinter Label widget to display status or count.
    :type label: tk.Label
    :param scanned_list: The list to store scanned operator names.
    :type scanned_list: List[str]
    :param operator_map: Mapping from operator IDs to operator names.
    :type operator_map: Dict[str, str]
    :param on_add: Optional callback function called with the operator name when added.
    :type on_add: Optional[Callable[[str], None]]
    :param error_if_missing: Whether to show an error if the operator ID is not found. Defaults to True.
    :type error_if_missing: bool, optional
    :return: A function that can be called to scan and add an operator.
    :rtype: Callable[[], None]
    """

    def update_listbox():
        """
        Update the listbox to reflect the current scanned operator list.

        :return: None
        """
        listbox.delete(0, tk.END)
        for op in scanned_list:
            listbox.insert(tk.END, op)

    def add_operator():
        """
        Scan the entry for an operator ID, validate, and add to the scanned list and listbox.

        Shows a warning if the operator is already scanned, or an error if not found (if enabled).
        Calls the on_add callback if provided.

        :return: None
        """
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
            show_error("Invalid Operator", f"ID '{op_id}' not recognized.")
        entry.delete(0, tk.END)
        entry.focus_set()

    return add_operator


def show_operator_modal(
    root: tk.Tk,
    station_name: str,
    modal_title: str,
    scan_label: str,
    operators_map: dict,
    submit_callback: Callable[[List[str], tk.Toplevel], None],
):
    """
    Show a modal dialog for operator sign-in or sign-out.

    :param root: The parent Tkinter root window.
    :param station_name: The name of the station.
    :param modal_title: The title for the modal window.
    :param scan_label: The label text for scanning operators.
    :param operators_map: Mapping from operator IDs to names.
    :param submit_callback: Function called with (scanned_operators, modal) on submit.
    """
    modal = make_modal(root, modal_title)

    tk.Label(
        modal,
        text=f"Station: {station_name}",
        font=("TkDefaultFont", 16),
    ).pack(pady=5)

    tk.Label(modal, text=scan_label).pack(pady=5)
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

    def update_listbox():
        operator_listbox.delete(0, tk.END)
        for op in scanned_operators:
            operator_listbox.insert(tk.END, op)
        operator_count.config(
            text=(
                f"{len(scanned_operators)} operators added."
                if scanned_operators
                else "No operators added."
            )
        )

    add_operator = make_operator_scanner(
        operator_entry,
        operator_listbox,
        operator_count,
        scanned_operators,
        operators_map,
    )

    operator_entry.bind("<Return>", lambda event: add_operator())

    def remove_selected_operator(event):
        selection = operator_listbox.curselection()
        if selection:
            idx = selection[0]
            op_name = operator_listbox.get(idx)
            if op_name in scanned_operators:
                scanned_operators.remove(op_name)
                update_listbox()

    operator_listbox.bind("<Double-Button-1>", remove_selected_operator)

    def on_submit():
        submit_callback(scanned_operators, modal)

    tk.Button(
        modal,
        text="Submit",
        command=on_submit,
        background="#5E5E5E",
        foreground="#ffffff",
    ).pack(pady=5)
    center_top_popup(root, modal, width=400)
