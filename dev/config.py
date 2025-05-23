from pathlib import Path
import csv
import sys
import os


def parse_station_info_file() -> tuple[list[str], str]:
    """Parses config.txt to extract station names and log directory."""
    possible_paths = [
        Path("../StationInfo/config.txt"),
        Path.cwd() / "config.txt",
    ]

    station_names = []
    log_dir = ""
    current_section = None

    for path in possible_paths:
        if not path.exists():
            continue

        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    if "Stations on PC" in line:
                        current_section = "stations"
                    elif "Log Directory" in line:
                        current_section = "log_dir"
                    else:
                        current_section = None
                    continue

                if current_section == "stations":
                    station_names.append(line)
                elif current_section == "log_dir":
                    log_dir = line

        break

    return station_names or ["Unknown"], log_dir


station_names, log_dir_path = parse_station_info_file()
log_dir = Path(log_dir_path)
log_dir.mkdir(parents=True, exist_ok=True)

EVENTS = {
    "Operator move": "Production",
    "Preparation": "Production",
    "Meeting": "Production",
    "Training": "Production",
    "No material": "Production",
    "Micro stoppage (Minor adjustment)": "Production",
    "Rework/Quality problems": "Quality",
    "Breakdown involving maintenance": "Maintenance",
    "Breakdown involving operation": "Maintenance",
    "Preventative Maintenance": "Planned",
    "No scheduled machine activity": "Planned",
    "Lunch": "Other",
    "Tea time": "Other",
    "Bathroom break": "Other",
    "Misc.": "Other",
}


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


OPERATORS = {}

csv_path = resource_path("data/operators.csv")

with open(csv_path, newline="") as csvfile:
    reader = csv.reader(csvfile)
    next(reader)
    for key, value in reader:
        OPERATORS[key] = value
