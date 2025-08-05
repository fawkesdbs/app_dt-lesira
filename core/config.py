"""Configuration utilities for station info, logging, events, and operator data.

This module provides functions and constants for parsing station configuration,
setting up log directories, mapping event categories, and loading operator data
from CSV files. It is intended to be imported and used by other modules in the
application.
"""

from pathlib import Path
import pytds
import sys
import os


def parse_station_info_file():
    """
    Parse the station configuration file to extract station names and log directory.

    Searches for 'config.txt' in possible locations, reads its contents, and extracts
    station names and the log directory path based on section headers.

    Returns:
        tuple[list[str], str]: A tuple containing a list of station names and the log directory path.
    """
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

    # return station_names or ["Unknown"], log_dir
    return station_names or ["Unknown"]


# station_names, log_dir_path = parse_station_info_file()
station_names = parse_station_info_file()
# log_dir = Path(log_dir_path)
# log_dir.mkdir(parents=True, exist_ok=True)

db_config = {
    "server": r"localhost",  # or server\instance_name
    "database": r"downtime_tracker",
    "user": r"Lesira",  # SQL Server username
    "password": r"Lesira",  # SQL Server password
}

# db_config = {
#     "server": r"192.168.1.11\SQL2012",  # or server\instance_name
#     "database": r"downtime_tracker",
#     "user": r"Siphamandla",  # SQL Server username
#     "password": r"nimysYrpRGWc1ir",  # SQL Server password
# }

def resource_path(relative_path):
    """
    Get the absolute path to a resource, compatible with development and PyInstaller.

    Args:
        relative_path (str): The relative path to the resource.

    Returns:
        str: The absolute path to the resource.
    """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def get_operators_from_db():
    """
    Fetch operators from the database.

    Returns:
        dict: A dictionary mapping operator_id to operator_name.
    """
    operators = {}
    try:
        conn = pytds.connect(
            server=db_config["server"],
            database=db_config["database"],
            user=db_config["user"],
            password=db_config["password"],
        )
        cursor = conn.cursor()
        # Both operator_id and operator_name are unique, but we use id as key
        cursor.execute("SELECT operator_id, operator_name FROM operators")
        for operator_id, operator_name in cursor.fetchall():
            operators[operator_id] = operator_name
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error loading operators from database: {e}")
    return operators


def get_events_from_db():
    """
    Fetch events and their categories from the database.

    Returns:
        dict: A dictionary mapping event_name (unique) to event_category.
    """
    events = {}
    try:
        conn = pytds.connect(
            server=db_config["server"],
            database=db_config["database"],
            user=db_config["user"],
            password=db_config["password"],
        )
        cursor = conn.cursor()
        # event_name is unique
        cursor.execute("SELECT event_name, event_category FROM events")
        for event_name, event_category in cursor.fetchall():
            events[event_name] = event_category
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error loading events from database: {e}")
    return events


OPERATORS = get_operators_from_db()
EVENTS = get_events_from_db()
